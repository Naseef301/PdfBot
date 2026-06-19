from __future__ import annotations

import logging
import threading
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from bm25 import create_bm25_index, load_bm25_index
from chunk import create_chunks
from embedding import create_vector_store, load_vector_store
from memory import ConversationState
from py_pdf import clean_text
from retrival import hybrid_retrieve
from rank import rerank_docs
from main import get_answer
from generateQuery import rewrite_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 30 * 1024 * 1024
UPLOAD_DIR = Path("uploads")

app = FastAPI(title="PDF RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

documents: dict[str, dict] = {}
conversation_states: dict[str, ConversationState] = {}
index_lock = threading.Lock()

def query_rag(question: str, state: ConversationState) -> tuple[str, list, str]:
    """Runs the complete RAG pipeline for a given query."""
    rewritten_query = rewrite_query(question, state)
    
    vector_store = load_vector_store()
    bm25_index, bm25_chunks = load_bm25_index()
    
    parent_docs = hybrid_retrieve(rewritten_query, vector_store, bm25_index, bm25_chunks)
    reranked_docs, best_score, is_relevant = rerank_docs(rewritten_query, parent_docs)
    
    history_str = state.get_formatted_history()
    answer, sources = get_answer(rewritten_query, reranked_docs, history_str=history_str)
    return answer, sources, rewritten_query


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None
    session_id: str | None = None
    history: list[dict] = Field(default_factory=list)


def _document_response(document_id: str) -> dict:
    record = documents.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "document_id": document_id,
        "status": record["status"],
        "message": record.get("message"),
        "document": {
            "filename": record["filename"],
            "size": record["size"],
            "pages": record.get("pages"),
            "chunks": record.get("chunks"),
        },
    }


def _index_document(document_id: str, pdf_path: Path) -> None:
    record = documents[document_id]
    try:
        with index_lock:
            pages = PyPDFLoader(str(pdf_path)).load()
            cleaned_pages = [
                Document(
                    page_content=text,
                    metadata={"source": record["filename"], "page": page_number},
                )
                for page_number, page in enumerate(pages)
                if (text := clean_text(page.page_content))
            ]
            if not cleaned_pages:
                raise ValueError("The PDF did not contain readable text.")

            chunks = create_chunks(cleaned_pages)
            create_vector_store(chunks, replace=True)
            create_bm25_index(chunks)

            for other_id, other_record in documents.items():
                if other_id != document_id and other_record["status"] == "ready":
                    other_record["status"] = "replaced"
                    other_record["message"] = "A newer document is now active."

            record.update(
                status="ready",
                message="Document indexed successfully.",
                pages=len(pages),
                chunks=len(chunks),
            )
            conversation_states[document_id] = ConversationState()
    except Exception as exc:
        logger.exception("Failed to index %s", record["filename"])
        record.update(status="error", message=str(exc))
    finally:
        pdf_path.unlink(missing_ok=True)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/upload", status_code=202)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict:
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    contents = await file.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="The PDF must be smaller than 30 MB.")
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    document_id = uuid.uuid4().hex
    try:
        UPLOAD_DIR.mkdir(exist_ok=True)
        pdf_path = UPLOAD_DIR / f"{document_id}.pdf"
        pdf_path.write_bytes(contents)
    except Exception as exc:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(status_code=500, detail="Could not save file to disk. Check permissions.")

    documents[document_id] = {
        "filename": filename,
        "size": len(contents),
        "status": "processing",
        "message": "Indexing document.",
    }
    background_tasks.add_task(_index_document, document_id, pdf_path)
    return _document_response(document_id)


@app.get("/api/status/{document_id}")
def document_status(document_id: str) -> dict:
    return _document_response(document_id)


@app.post("/api/query")
def ask_document(request: QueryRequest) -> dict:
    document_id = request.document_id or request.session_id
    if not document_id:
        raise HTTPException(status_code=400, detail="A document ID is required.")

    record = documents.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if record["status"] != "ready":
        raise HTTPException(
            status_code=409,
            detail=record.get("message") or "Document is not ready.",
        )

    question = request.question.strip()

    state = conversation_states.setdefault(document_id, ConversationState())
    try:
        with index_lock:
            answer, sources, rewritten = query_rag(question, state)
        state.add_turn(question, answer, rewritten_query=rewritten)
        return {
            "answer": answer,
            "sources": sources,
            "metadata": {"document_id": document_id},
        }
    except Exception as exc:
        logger.exception("Query failed for document %s", document_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
