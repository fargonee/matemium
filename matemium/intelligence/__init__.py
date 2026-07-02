"""Local intelligence: embeddings, vector DB, RAG (lazy loaded)."""

from .retriever import VectorRetriever, KeywordRetriever, get_retriever

__all__ = ["VectorRetriever", "KeywordRetriever", "get_retriever"]