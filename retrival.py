import logging
from typing import Dict, Iterable, List, Tuple

from langchain_core.documents import Document

from bm25 import bm25_search
from generateQuery import generate_multi_queries
from config import TOP_K_BM25, TOP_K_DENSE

logger = logging.getLogger(__name__)

# Controls how much lower-ranked documents matter in fusion.
# Lower values make fusion more top-heavy (favoring higher ranks more strongly).
_RRF_K = 60

def _reciprocal_rank_fusion(ranked_lists: List[List[Document]]) -> List[Document]:
    """
    Fuse multiple ranked lists of Documents using Reciprocal Rank Fusion (RRF).

    RRF is used instead of mixing raw dense and BM25 scores because their
    numeric scales are not directly comparable. RRF only relies on rank
    positions, making it robust when combining heterogeneous retrievers.

    Args:
        ranked_lists: A list of ranked Document lists (best to worst).

    Returns:
        A single list of Documents ranked by fused RRF score.
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    for ranked in ranked_lists:
        for rank_idx, doc in enumerate(ranked, start=1):
            parent_hash = doc.metadata.get("parent_hash")
            if parent_hash:
                doc_id = str(parent_hash)
            else:
                # Fallback identity if no parent_hash is available
                doc_id = str(hash(doc.page_content))

            # RRF scoring: higher rank (smaller rank_idx) -> larger contribution
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (_RRF_K + rank_idx)
            # Keep the latest instance (they should be equivalent)
            doc_map[doc_id] = doc

    # Sort document IDs by fused score (descending)
    sorted_ids = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)
    return [doc_map[doc_id] for doc_id in sorted_ids]

def dense_search(
    query: str,
    vector_store,
    top_k: int = TOP_K_DENSE,
) -> List[Document]:
    """
    Run dense vector search against the vector store and return ranked Documents.

    Uses similarity_search_with_score, which returns (Document, distance) tuples,
    where lower distance means better match.

    Args:
        query: User query string.
        vector_store: Vector store object exposing similarity_search_with_score.
        top_k: Maximum number of results to return.

    Returns:
        A list of Documents ranked by ascending distance.
    """
    try:
        results: Iterable[Tuple[Document, float]] = vector_store.similarity_search_with_score(
            query, k=top_k
        )
    except Exception as exc:
        logger.error("Dense search failed for query %r: %s", query, exc)
        return []

    # Sort by distance (ascending: lower is better) and strip out the docs
    # pair[1] guarantees we're sorting purely by the float score
    sorted_docs = sorted(results, key=lambda pair: pair[1])

    return [doc for doc, _dist in sorted_docs]

def _reconstruct_parents(docs: List[Document]) -> List[Document]:
    """
    Reconstruct parent-level Documents from retrieved child chunks.

    Retrieved documents are child chunks that carry parent metadata:
      - parent_hash: stable identifier for the parent chunk
      - parent_content: full text of the parent chunk

    This function:
      - Deduplicates parent chunks using parent_hash
      - Creates new parent-level Documents with page_content set to
        parent_content and metadata copied from the child
      - Falls back to using the child chunk itself if parent_content
        is missing, deduplicating by page_content

    Args:
        docs: List of child-level Documents.

    Returns:
        A list of parent-level Documents, deduplicated and ready for reranking.
    """
    parents: List[Document] = []
    
    # Using python sets is more idiomatic and optimal for membership testing
    seen_parents = set()
    seen_fallback = set()

    for doc in docs:
        parent_hash = doc.metadata.get("parent_hash")
        parent_content = doc.metadata.get("parent_content")

        if parent_hash and parent_content:
            key = str(parent_hash)
            if key in seen_parents:
                continue
            seen_parents.add(key)

            parent_doc = Document(
                page_content=parent_content,
                metadata={**doc.metadata},
            )
            parents.append(parent_doc)
        else:
            # Fallback to child chunk if parent info is missing
            content_key = doc.page_content
            if content_key in seen_fallback:
                continue
            seen_fallback.add(content_key)
            parents.append(doc)

    return parents

def hybrid_retrieve(
    query: str,
    vector_store,
    bm25,
    chunks: List[Document],
) -> List[Document]:
    """
    Perform hybrid retrieval combining dense search, BM25, multi-query expansion,
    reciprocal rank fusion, and parent-child reconstruction.

    Steps:
      1. Generate multiple query variants using generate_multi_queries(query)
      2. For each variant:
         - Run dense search against the vector_store
         - Run BM25 sparse search via bm25_search
      3. Collect all non-empty ranked lists
      4. If no lists exist, log a warning and return []
      5. Fuse all ranked lists using Reciprocal Rank Fusion (RRF)
      6. Reconstruct parent chunks from fused child-level results
      7. Return parent-level Documents ready for downstream reranking

    Args:
        query: Original user query.
        vector_store: Dense vector store for similarity search.
        bm25: BM25 index object used by bm25_search.
        chunks: List of child chunk Documents (BM25 corpus).

    Returns:
        A list of parent-level Documents ranked by fused hybrid retrieval.
    """
    queries = generate_multi_queries(query)
    logger.debug("Hybrid retrieve: %d queries", len(queries))

    ranked_lists: List[List[Document]] = []

    for q in queries:
        # Dense retrieval over child chunks
        dense_docs = dense_search(q, vector_store, top_k=TOP_K_DENSE)

        # Sparse BM25 retrieval over child chunks
        try:
            # Addressed mismatch parameter: top_k -> k
            bm25_docs = bm25_search(q, bm25, chunks, k=TOP_K_BM25)
        except Exception as exc:
            logger.error("BM25 search failed for query %r: %s", q, exc)
            bm25_docs = []

        if dense_docs:
            ranked_lists.append(dense_docs)
        if bm25_docs:
            ranked_lists.append(bm25_docs)

    if not ranked_lists:
        logger.warning("Hybrid retrieve: no results for query %r", query)
        return []

    total_retrieved = sum(len(lst) for lst in ranked_lists)
    fused_docs = _reciprocal_rank_fusion(ranked_lists)
    logger.debug(
        "Hybrid retrieve: fused %d documents (%d unique after RRF)",
        total_retrieved,
        len(fused_docs),
    )

    parents = _reconstruct_parents(fused_docs)
    logger.info(
        "Hybrid retrieve: %d unique parent chunks returned",
        len(parents),
    )

    return parents
