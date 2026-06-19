import pickle
import os
import logging
import re
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from config import BM25_PATH

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    nltk.download("stopwords", quiet=True)
    STOP_WORDS = set(stopwords.words("english"))
    _stemmer = PorterStemmer()
    _USE_NLTK = True
except ImportError:
    logging.warning("NLTK not available.")
    STOP_WORDS = set()
    _stemmer = None
    _USE_NLTK = False

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """
    Shared tokenizer for both indexing and querying.
    Must be identical in both places — asymmetric tokenization silently kills BM25.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()

    if _USE_NLTK:
        tokens = [
            _stemmer.stem(t)
            for t in tokens
            if t not in STOP_WORDS and len(t) > 1
        ]
    else:
        tokens = [t for t in tokens if len(t) > 1]

    return tokens


def create_bm25_index(chunks: list[Document]):
    """
    Creates and persists a BM25 index for sparse keyword retrieval.
    """
    if not chunks:
        raise ValueError("Cannot create BM25 index from empty chunk list.")

    texts = [doc.page_content for doc in chunks]
    tokenized_corpus = [_tokenize(text) for text in texts]
    
    # Warn about empty token lists (e.g. very short or symbol-heavy chunks)
    empty_count = sum(1 for t in tokenized_corpus if not t)
    if empty_count:
        logger.warning(f"BM25: {empty_count}/{len(chunks)} chunks produced empty token lists.")

    bm25 = BM25Okapi(tokenized_corpus)
    logger.info(f"BM25 index built: {len(chunks)} chunks, vocab size ≈ {len(bm25.idf)}")

    # Save chunks alongside the BM25 index so we can map results back to documents
    os.makedirs(os.path.dirname(BM25_PATH), exist_ok=True)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks}, f)
        
    logger.info("BM25 index saved to %s", BM25_PATH)


def load_bm25_index() -> tuple[BM25Okapi, list[Document]]:
    """
    Loads the persisted BM25 index and corresponding chunks.
    """
    if not os.path.exists(BM25_PATH):
        raise FileNotFoundError(f"BM25 index not found at '{BM25_PATH}'")
        
    with open(BM25_PATH, "rb") as f:
        data = pickle.load(f)
        
    logger.info("BM25 index loaded from %s", BM25_PATH)
    return data["bm25"], data["chunks"]


def bm25_search(query: str, bm25_index: BM25Okapi, chunks: list[Document], k: int = 5) -> list[Document]:
    """
    Run BM25 keyword retrieval.

    Returns top_k chunks with score > 0 (zero-score = no term overlap = noise).
    """
    tokenized_query = _tokenize(query)

    if not tokenized_query:
        logger.warning(f"BM25: query '{query}' produced empty token list after normalization.")
        return []

    scores = bm25_index.get_scores(tokenized_query)

    # Sort descending, filter zero scores to avoid returning random noise
    ranked = sorted(
        enumerate(scores),
        key=lambda x: x[1],
        reverse=True
    )

    results = [chunks[idx] for idx, score in ranked[:k] if score > 0.0]

    top_score = ranked[0][1] if ranked else 0.0
    logger.debug(f"BM25: query='{query}' → {len(results)} results (top score: {top_score:.3f})")
    return results
