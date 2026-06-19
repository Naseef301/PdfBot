# Configuration settings
# OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_MODEL = "llama3.2:latest"

CHROMA_PATH = "vector/chroma_db"
COLLECTION_NAME = "rag_documents"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
BM25_PATH = "vector/bm25_index.pkl"

# Parent chunks: large enough for full context
PARENT_CHUNK_SIZE = 1500
PARENT_CHUNK_OVERLAP = 200

# Child chunks: small enough for precise retrieval
CHILD_CHUNK_SIZE = 400
CHILD_CHUNK_OVERLAP = 80



TOP_K_DENSE = 10          # Dense results per query
TOP_K_BM25 = 10           # BM25 results per query
TOP_K_RERANK = 5          # Final docs sent to LLM after reranking
MULTI_QUERY_COUNT = 3    # Number of multi-queries to generate (excluding original question)
MEMORY_WINDOW = 3        # Number of recent turns to keep in memory context


RERANKER_HARD_FLOOR = -15.0  # Logit threshold below which results are deemed deeply irrelevant