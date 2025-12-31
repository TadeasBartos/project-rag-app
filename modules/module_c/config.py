"""
Configuration for module_c (bimGPT).
Module-specific settings for RAG system behavior.
"""

# LLM Configuration
LLM_MODEL = "gemma2:2b"
EMBEDDING_MODEL = "nomic-embed-text"

# Retrieval Configuration
SIMILARITY_TOP_K = 5  # Number of top chunks to send to LLM
DISTANCE_METRIC = "l2"  # Options: "l2", "cosine", "ip"

# Reranker Configuration
ENABLE_RERANKING = False  # Use cross-encoder to rerank results
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_K = 20  # Get more initial results to rerank

# Chunking Configuration
MAX_CHUNK_SIZE = 1000  # Maximum characters per chunk
MIN_CHUNK_SIZE = 200   # Minimum characters per chunk
PRESERVE_CONTEXT_LINES = 1  # Number of parent headers to include

# Module Metadata
MODULE_NAME = "bimGPT"
MODULE_DESCRIPTION = "ISO 19650 Knowledge Master"


