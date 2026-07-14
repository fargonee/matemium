"""Local intelligence: embeddings, vector DB, RAG, and advanced chunking (lazy loaded)."""

from .retriever import VectorRetriever, KeywordRetriever, get_retriever
from .chunking import CHUNKING_METHODS, autodetect_and_chunk

__all__ = [
    "VectorRetriever",
    "KeywordRetriever",
    "get_retriever",
    "CHUNKING_METHODS",
    "autodetect_and_chunk",
]