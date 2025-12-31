"""
Configuration for module_b (civilGPT).
Module-specific settings for RAG system behavior.
"""

# LLM Configuration
LLM_MODEL = "gemma2:2b"
EMBEDDING_MODEL = "nomic-embed-text"

# Retrieval Configuration
SIMILARITY_TOP_K = 7  # Number of top chunks to send to LLM (more for technical content)
DISTANCE_METRIC = "l2"  # Options: "l2", "cosine", "ip"

# Reranker Configuration
ENABLE_RERANKING = True  # Enable reranking for better accuracy on technical queries
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_K = 25  # Get more initial results to rerank for technical content

# Chunking Configuration
MAX_CHUNK_SIZE = 1200  # Larger chunks for technical documentation
MIN_CHUNK_SIZE = 250   # Minimum characters per chunk
PRESERVE_CONTEXT_LINES = 2  # More context for technical hierarchies

# Module Metadata
MODULE_NAME = "civilGPT"
MODULE_DESCRIPTION = "Civil 3D Command Knowledge Base"

