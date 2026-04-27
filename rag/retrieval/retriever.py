"""
rag/retrieval/retriever.py
KnowledgeRetriever — loads the persisted FAISS index and performs similarity search.
"""
from __future__ import annotations

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_PATH      = "rag/index/faiss_store"


class KnowledgeRetriever:
    _instance: "KnowledgeRetriever | None" = None  # singleton cache

    def __init__(self, index_path: str = INDEX_PATH):
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS

        self.index_path = index_path
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.store = FAISS.load_local(
            index_path,
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        print(f"✅ KnowledgeRetriever loaded from {index_path}")

    @classmethod
    def get_instance(cls) -> "KnowledgeRetriever":
        """Singleton — avoids reloading the embedding model on every request."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Force reload — call after rebuilding the index."""
        cls._instance = None

    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        """Return top-k most relevant chunks with similarity scores."""
        results = self.store.similarity_search_with_score(query, k=k)
        return [
            {
                "content": doc.page_content,
                "source":  doc.metadata.get("source", "unknown"),
                "score":   round(float(score), 4),
            }
            for doc, score in results
        ]

    def index_available(self) -> bool:
        """Returns True if the FAISS index exists on disk."""
        from pathlib import Path
        return (Path(self.index_path) / "index.faiss").exists()


def retriever_available() -> bool:
    """Quick check without loading the model."""
    from pathlib import Path
    return (Path(INDEX_PATH) / "index.faiss").exists()
