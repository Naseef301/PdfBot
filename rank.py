import logging

from sentence_transformers import CrossEncoder

from config import RERANKER_HARD_FLOOR, TOP_K_RERANK

logger = logging.getLogger(__name__)

# Load the reranker only once because the model is expensive to initialize.
_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    """Return a cached CrossEncoder reranker instance."""
    global _reranker

    if _reranker is None:
        logger.info("Loading reranker model: cross-encoder/ms-marco-MiniLM-L-6-v2")
        _reranker = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512,
        )
        logger.info("Reranker model loaded.")

    return _reranker


def rerank_docs(
    query: str,
    docs: list,
    top_k: int = TOP_K_RERANK,
) -> tuple[list, float, bool]:
    """
    Rerank retrieved documents using a cross-encoder model.

    Returns:
        - top_docs: the top_k documents after reranking
        - best_score: the highest raw logit score across all input documents
        - is_relevant: False only when all results appear deeply irrelevant

    Notes:
        - Scores are raw logits from cross-encoder/ms-marco-MiniLM-L-6-v2, not
          calibrated probabilities.
        - The hard floor is only a last-resort safety net for deeply irrelevant
          results and should not be treated as the main decision gate.
    """
    if not docs:
        return ([], float("-inf"), False)

    reranker = _get_reranker()
    pairs = [(query, doc.page_content) for doc in docs]

    try:
        scores = reranker.predict(pairs)
    except Exception as exc:
        logger.error(
            "Reranker prediction failed: %s. Returning docs in original order.",
            exc,
        )
        return (docs[:top_k], 0.0, True)

    scored_docs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    best_score = float(scored_docs[0][0]) if scored_docs else float("-inf")
    is_relevant = best_score > RERANKER_HARD_FLOOR

    # Only keep documents that meet the minimum score threshold
    top_docs = [doc for score, doc in scored_docs[:top_k] if score > RERANKER_HARD_FLOOR]

    logger.debug(
        "Reranker: %d docs → top %d, best score: %.3f, relevant: %s",
        len(docs),
        len(top_docs),
        best_score,
        is_relevant,
    )

    return (top_docs, best_score, is_relevant)