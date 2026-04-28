# FAISS Setup Visualization

This project uses a persisted LangChain FAISS vector store as the local knowledge
index for the AI copilot and alert explanation flows.

## Current Index State

```text
rag/docs/
  battery_oem_manual.txt
  cve_advisories.txt
  cyber_battery_fusion_guide.txt
  ids_incident_playbook.txt
  thermal_runaway_sop.txt

rag/index/faiss_store/
  index.faiss
  index.pkl
```

The index is built with `sentence-transformers/all-MiniLM-L6-v2` on CPU, using
normalized embeddings.

## Build-Time Flow

```mermaid
flowchart LR
    A["Knowledge docs<br/>rag/docs/*.txt"] --> B["chunk_documents()<br/>rag/ingestion/chunker.py"]
    B --> C["RecursiveCharacterTextSplitter<br/>512 chars, 64 overlap"]
    C --> D["LangChain Document chunks<br/>source + full_path metadata"]
    D --> E["HuggingFaceEmbeddings<br/>all-MiniLM-L6-v2<br/>CPU, normalized"]
    E --> F["FAISS.from_documents()"]
    F --> G["store.save_local()<br/>rag/index/faiss_store"]
    G --> H["index.faiss<br/>vector index"]
    G --> I["index.pkl<br/>docstore + metadata"]
```

Build command:

```powershell
python rag/ingestion/build_index.py
```

## Query-Time Flow

```mermaid
flowchart TD
    UI["Next.js frontend"] --> API["FastAPI backend"]
    API --> Status["GET /copilot/status"]
    Status --> ReadyCheck["retriever_available()<br/>checks index.faiss"]

    API --> Chat["POST /copilot/chat"]
    Chat --> Chain["ConversationalChain"]
    Chain --> Intent{"classify_intent()"}

    Intent -->|"sop_lookup"| SOP["Retrieve message directly<br/>k = 4"]
    Intent -->|"general"| General["Retrieve message directly<br/>k = 3"]
    Intent -->|"alert_query + asset_context"| Alert["AlertRAGChain"]

    Alert --> AlertQuery["Build alert query from<br/>asset, risk, threat, LIME contributors"]
    AlertQuery --> AlertRetrieve["KnowledgeRetriever.retrieve()<br/>k = 5"]
    SOP --> Retriever["KnowledgeRetriever singleton"]
    General --> Retriever
    AlertRetrieve --> Retriever

    Retriever --> Load["FAISS.load_local()<br/>rag/index/faiss_store"]
    Load --> EmbedQuery["Embed query with same model"]
    EmbedQuery --> Search["similarity_search_with_score()"]
    Search --> Context["Top chunks<br/>content, source, score"]

    Context --> Prompt["Prompt builder"]
    Prompt --> Gemini["Gemini 1.5 Flash"]
    Gemini --> Response["Answer + sources + context_count"]
    Response --> UI
```

## Main Components

| Area | File | Role |
| --- | --- | --- |
| Chunking | `rag/ingestion/chunker.py` | Reads `.txt` docs and creates overlapping LangChain `Document` chunks. |
| Index build | `rag/ingestion/build_index.py` | Embeds chunks and saves the FAISS store to disk. |
| Retrieval | `rag/retrieval/retriever.py` | Loads the persisted store and exposes singleton top-k similarity search. |
| Alert RAG | `rag/chains/alert_chain.py` | Builds an alert-specific query, retrieves top 5 chunks, and grounds Gemini output. |
| Copilot RAG | `rag/chains/conversational_chain.py` | Routes user intent and retrieves context for SOP/general/copilot requests. |
| API status | `backend/routers/copilot.py` | Reports whether `index.faiss` exists and whether `GEMINI_API_KEY` is set. |
| Frontend status | `frontend/src/lib/api.ts` | Types and calls the copilot status/chat endpoints. |

## Operational Notes

- Rebuild the index after changing files in `rag/docs/`.
- `KnowledgeRetriever` is cached as a singleton, so call `KnowledgeRetriever.reset()`
  if the app process needs to reload a freshly rebuilt index without restarting.
- `allow_dangerous_deserialization=True` is required by the current LangChain FAISS
  loader because `index.pkl` contains the persisted docstore metadata.
