import hashlib
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import (
    PARENT_CHUNK_SIZE,
    PARENT_CHUNK_OVERLAP,
    CHILD_CHUNK_SIZE,
    CHILD_CHUNK_OVERLAP,
)

logger = logging.getLogger(__name__)


def _content_hash(text: str) -> str:
    """Return a short MD5 fingerprint used for fast deduplication."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def create_chunks(documents: list[Document]) -> list[Document]:
    """
    Create two-level parent-child chunks for retrieval.

    Parent chunks are larger context windows and their full text is stored in each
    child chunk's metadata for context reconstruction. Child chunks are smaller,
    retrieval-friendly units that are intended to be embedded and stored in the
    vector database.

    Each returned child chunk carries the following metadata fields:
    - parent_id: integer index of the parent chunk
    - parent_content: full text of the parent chunk
    - parent_hash: short MD5 fingerprint of the parent chunk
    - source: source filename or identifier
    - page: original 0-based page number
    """
    if not documents:
        raise ValueError("Cannot chunk empty document list.")

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=PARENT_CHUNK_SIZE,
        chunk_overlap=PARENT_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK_SIZE,
        chunk_overlap=CHILD_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    parent_chunks = parent_splitter.split_documents(documents)
    logger.info(
        "Chunking: %s pages → %s parent chunks",
        len(documents),
        len(parent_chunks),
    )

    child_chunks: list[Document] = []

    for parent_idx, parent in enumerate(parent_chunks):
        parent_hash = _content_hash(parent.page_content)
        children = child_splitter.split_documents([parent])

        for child in children:
            child.metadata.update(
                {
                    "parent_id": parent_idx,
                    "parent_content": parent.page_content,
                    "parent_hash": parent_hash,
                    "source": parent.metadata.get("source", "unknown"),
                    "page": parent.metadata.get("page", 0),
                }
            )
            child_chunks.append(child)

    logger.info(
        "Chunking: %s parents → %s child chunks",
        len(parent_chunks),
        len(child_chunks),
    )

    if len(child_chunks) < 5:
        logger.warning(
            "Only %s chunks created from %s pages. Check PDF quality / cleaning pipeline.",
            len(child_chunks),
            len(documents),
        )

    return child_chunks