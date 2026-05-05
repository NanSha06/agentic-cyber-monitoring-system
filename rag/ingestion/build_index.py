"""
rag/ingestion/build_index.py
Builds and persists the FAISS vector store from knowledge documents.

Usage:
    python rag/ingestion/build_index.py
"""
from __future__ import annotations
import os
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_JAX", "0")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_PATH      = "rag/index/faiss_store"
DOC_DIR         = "rag/docs"


def build_faiss_index(doc_dir: str = DOC_DIR, index_path: str = INDEX_PATH):
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from rag.ingestion.chunker import chunk_documents

    print("=" * 55)
    print("[*] Building FAISS Knowledge Index")
    print("=" * 55)

    # 1. Chunk all documents
    print(f"\n[+] Chunking documents from: {doc_dir}")
    chunks = chunk_documents(doc_dir)

    # 2. Load embedding model
    print(f"\n[+] Loading embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # 3. Build FAISS index
    print(f"\n[+] Embedding {len(chunks)} chunks...")
    store = FAISS.from_documents(chunks, embeddings)

    # 4. Persist to disk
    Path(index_path).mkdir(parents=True, exist_ok=True)
    store.save_local(index_path)

    print(f"\n[OK] FAISS index saved -> {index_path}")
    print(f"   Chunks indexed: {len(chunks)}")
    return store


if __name__ == "__main__":
    build_faiss_index()
