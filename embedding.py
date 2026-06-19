import logging
import os
import torch

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

_embedding_model: HuggingFaceEmbeddings | None = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Return a cached HuggingFace embedding model.

    The first call loads and caches the model (may download weights from HuggingFace Hub).
    Subsequent calls return the cached instance without reloading.
    """
    global _embedding_model

    if _embedding_model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        device = "cuda" if torch.cuda.is_available() else "cpu"

        _embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},  # L2-normalized, cosine-ready
        )

        logger.info("Embedding model loaded: %s", EMBEDDING_MODEL)

    return _embedding_model


# def create_vector_store(chunks: list) -> Chroma:
def create_vector_store(chunks: list[Document], replace: bool = False) -> Chroma:
    """
    Embed the provided document chunks and persist them as a Chroma collection.

    Args:
        chunks: List of LangChain Document objects (child chunks from chunking.py).

    Returns:
        A persistent Chroma vector store instance.

    Raises:
        ValueError: If chunks list is empty.
    """
    if not chunks:
        raise ValueError("Cannot create vector store from empty chunk list.")

    embeddings = get_embedding_model()

    logger.info("Embedding %d chunks → Chroma at '%s'", len(chunks), CHROMA_PATH)

    if replace and os.path.exists(CHROMA_PATH):
        existing_store = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )
        try:
            existing_store.delete_collection()
        except ValueError:
            logger.info("No existing vector collection to replace.")

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
    )

    logger.info(
        "Vector store created: collection='%s', path='%s'",
        COLLECTION_NAME,
        CHROMA_PATH,
    )

    return vector_store


def load_vector_store() -> Chroma:
    """
    Load an existing Chroma vector store from disk.

    Uses the same embedding model that was used during ingestion to ensure
    query vectors are in the same space as stored document vectors.

    Returns:
        A Chroma vector store instance connected to the persisted collection.

    Raises:
        Exception: If the Chroma collection does not exist at CHROMA_PATH.
    """
    if not os.path.exists(CHROMA_PATH):
        raise FileNotFoundError(f"Chroma vector store not found at '{CHROMA_PATH}'")

    embeddings = get_embedding_model()

    vector_store = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )

    logger.info(
        "Vector store loaded: collection='%s', path='%s'",
        COLLECTION_NAME,
        CHROMA_PATH,
    )

    return vector_store
