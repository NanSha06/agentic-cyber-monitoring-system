"""
rag/retrieval/retriever.py
KnowledgeRetriever â€” loads the persisted FAISS index and performs similarity search.
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
        print(f"[OK] KnowledgeRetriever loaded from {index_path}")

    @classmethod
    def get_instance(cls) -> "KnowledgeRetriever":
        """Singleton â€” avoids reloading the embedding model on every request."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Force reload â€” call after rebuilding the index."""
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

    def retrieve_mmr(self, query: str, k: int = 7, fetch_k: int = 20, lambda_mult: float = 0.6) -> list[dict]:
        """
        Retrieve k chunks using Maximum Marginal Relevance (MMR).

        MMR balances relevance with diversity: it penalises chunks that are
        too similar to already-selected ones. This ensures a multi-phase SOP
        returns chunks from Phase 1, Phase 2, Phase 3 etc. rather than
        repeating the highest-scoring section.

        Args:
            query:       Search query string.
            k:           Number of final chunks to return.
            fetch_k:     Candidate pool size before MMR re-ranking (>= k).
            lambda_mult: 1.0 = pure similarity, 0.0 = pure diversity.
        """
        docs = self.store.max_marginal_relevance_search(
            query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
        )
        return [
            {
                "content": doc.page_content,
                "source":  doc.metadata.get("source", "unknown"),
                "score":   0.0,   # MMR does not expose a scalar score
            }
            for doc in docs
        ]

    def index_available(self) -> bool:
        """Returns True if the FAISS index exists on disk."""
        from pathlib import Path
        return (Path(self.index_path) / "index.faiss").exists()


def retriever_available() -> bool:
    """Quick check without loading the model."""
    from pathlib import Path
    return (Path(INDEX_PATH) / "index.faiss").exists()
