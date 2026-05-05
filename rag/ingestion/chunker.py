"""
rag/ingestion/chunker.py
Splits knowledge documents into overlapping chunks for embedding.
"""
from __future__ import annotations
from pathlib import Path

CHUNK_SIZE    = 512   # characters (not tokens — LangChain default)
CHUNK_OVERLAP = 64


def chunk_documents(doc_dir: str = "rag/docs") -> list:
    """Return a list of LangChain Document objects from all .txt files in doc_dir."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )

    path = Path(doc_dir)
    if not path.exists():
        raise FileNotFoundError(f"Document directory not found: {doc_dir}")

    chunks = []
    txt_files = sorted(path.rglob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No .txt files found in {doc_dir}")

    for fpath in txt_files:
        text = fpath.read_text(encoding="utf-8")
        docs = splitter.create_documents(
            [text],
            metadatas=[{"source": fpath.name, "full_path": str(fpath)}],
        )
        chunks.extend(docs)
        print(f"  [+] {fpath.name} -> {len(docs)} chunks")

    print(f"[OK] Total chunks: {len(chunks)}")
    return chunks
