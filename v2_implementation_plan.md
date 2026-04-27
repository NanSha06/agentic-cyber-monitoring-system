# 🧠 V2 — Intelligence Layer: Implementation Plan
## RAG Knowledge Grounding + AI Copilot (Weeks 7–10)

> **Goal:** Every alert is enriched with retrieved incident context and grounded AI explanation. Operators can ask the AI copilot natural-language questions about any asset.

---

## Current State (V1 ✅ Complete)

| Component | Status |
|-----------|--------|
| Data pipeline → `unified.parquet` | ✅ Built |
| 5 ML models (SOH, RUL, Anomaly, Classifier, Autoencoder) | ✅ Built |
| LIME explainability | ✅ Built |
| FastAPI backend (17 routes + WebSocket) | ✅ Running |
| Next.js dashboard (Command Center, Assets, Explain) | ✅ Running |

---

## V2 Architecture

```
Alert (risk > 60)
      │
      ▼
  LIME Explainer ──────────────────────────────────────┐
      │                                                 │
      ▼                                                 ▼
  Query Builder                               Feature contributions
      │
      ▼
  KnowledgeRetriever (FAISS)
      │  top-5 similar chunks from:
      │   • OEM battery manuals
      │   • CVE advisories
      │   • Incident SOP docs
      │   • CIC-IDS threat reports
      │
      ▼
  AlertRAGChain (Gemini 1.5 Flash)
      │  prompt = system + alert summary + retrieved context
      │
      ▼
  Grounded Response + Source Citations
      │
      ├──► /copilot/chat  (FastAPI)
      │
      └──► Copilot UI (Next.js)
               • Chat messages
               • Source panel
               • Suggested actions
               • "Ask AI" button on every alert
```

---

## Week-by-Week Build Plan

### Week 7 — Document Corpus & FAISS Vector Store

#### Files to Create
```
rag/
├── docs/                          ← knowledge documents (seed content)
│   ├── battery_oem_manual.txt
│   ├── thermal_runaway_sop.txt
│   ├── cve_advisories.txt
│   ├── ids_incident_playbook.txt
│   └── cyber_battery_fusion_guide.txt
├── ingestion/
│   ├── chunker.py                 ← RecursiveCharacterTextSplitter
│   └── build_index.py             ← FAISS index builder + saver
├── retrieval/
│   └── retriever.py               ← KnowledgeRetriever class
└── index/                         ← persisted FAISS store (gitignored)
```

#### Key Decisions
| Decision | Choice | Reason |
|---|---|---|
| Embedding model | `all-MiniLM-L6-v2` | 384-dim, fast on CPU, high quality |
| Chunk size | 512 tokens | Balances context vs. retrieval precision |
| Chunk overlap | 64 tokens | Prevents context loss at boundaries |
| Top-k retrieval | k=5 | Enough context without overwhelming the prompt |
| Index persistence | `rag/index/faiss_store/` | Avoid rebuilding on every restart |

#### Deliverable
- [ ] 5 seed knowledge documents created in `rag/docs/`
- [ ] FAISS index built: `python rag/ingestion/build_index.py`
- [ ] Retriever returns top-5 chunks for any test query
- [ ] Index size < 50 MB (CPU-feasible)

---

### Week 8 — Gemini Integration & RAG Chain

#### Files to Create
```
rag/
└── chains/
    ├── alert_chain.py             ← AlertRAGChain (Gemini + retriever)
    ├── sop_chain.py               ← SOP lookup chain
    └── prompts.py                 ← All system prompt templates
```

#### Prompt Template Design
```
SYSTEM:
  You are an expert systems engineer for cyber-physical asset management.
  You have: (1) an alert + LIME contributions, (2) retrieved context.
  Task: explain root cause in plain English + top 3 mitigations.
  Always cite sources. Max 3 paragraphs.

ALERT:
  Asset {asset_id} — Risk {risk_score}/100
  Factors: {lime_top4_contributions}
  Threat: {threat_type}

CONTEXT:
  [Source: battery_oem_manual.txt]  ...
  ---
  [Source: cve_advisories.txt]  ...
```

#### Gemini Safety: Retry + Fallback
```python
# Retry on rate limit → exponential backoff (1s, 2s, 4s)
# Fallback: return LIME explanation alone if Gemini fails
# Cache: store responses keyed by alert_id (avoid re-calling API)
```

#### Deliverable
- [ ] `GEMINI_API_KEY` in `.env`
- [ ] RAG chain returns grounded answer + source list for any alert
- [ ] Response latency < 8 seconds
- [ ] Fallback returns LIME-only explanation if API fails

---

### Week 9 — AI Copilot Backend

#### Files to Create / Modify
```
backend/
└── routers/
    └── copilot.py                 ← /copilot/chat endpoint

rag/
└── chains/
    └── conversational_chain.py    ← multi-turn conversation manager
```

#### Intent Classification
```
User message → intent classifier
    │
    ├── "Why is Tower-12 risky?"    → alert_query  → AlertRAGChain
    ├── "What is the SOP for DDoS?" → sop_lookup   → SOPChain
    └── "What is SOH?"              → general       → Gemini direct
```

#### Conversation History Schema
```python
history = [
    {"role": "user",      "content": "Why is Tower-12 risky?"},
    {"role": "assistant", "content": "Tower-12 shows elevated temp..."},
    {"role": "user",      "content": "What should I do first?"},
]
# Last 5 turns included in prompt context (token budget ~1500)
```

#### Rate Limiting
- 10 requests/minute per session (session ID from cookie/header)
- Returns `429 Too Many Requests` with retry-after header

#### Deliverable
- [ ] `POST /copilot/chat` endpoint live
- [ ] Copilot correctly routes 3 intent types
- [ ] 5-turn conversation with history maintained
- [ ] "Why is Tower-12 risky?" returns grounded, cited response

---

### Week 10 — AI Copilot UI & V2 Polish

#### Files to Create (Frontend)
```
frontend/src/app/
└── copilot/
    └── page.tsx                   ← Full chat UI page

frontend/src/components/
├── CopilotChat.tsx                ← Message thread + input box
├── SourcePanel.tsx                ← Source citations sidebar
└── SuggestedPrompts.tsx           ← Quick-action prompt chips
```

#### UI Features
| Feature | Description |
|---|---|
| Chat interface | Streaming message display, user + assistant bubbles |
| Suggested prompts | "Why is this asset risky?", "What's the SOP?", "Explain LIME" |
| Source citation panel | Shows document name + relevance score for each response |
| "Ask AI" button | On every alert card → opens Copilot pre-filled with alert context |
| Loading skeleton | Animated "thinking" indicator while Gemini responds |
| Copy response | Copy button on each assistant message |

#### Nav Update
```
Command Center → Assets → Explain → Copilot (NEW)
```

---

## V2 Dependency Installation

```bash
pip install langchain==0.2.0 langchain-community==0.2.0 \
            faiss-cpu==1.8.0 \
            sentence-transformers==3.0.0 \
            google-generativeai==0.7.0
```

## Prerequisites Before Starting

- [ ] `GEMINI_API_KEY` obtained from [Google AI Studio](https://aistudio.google.com)
- [ ] Add to `.env`: `GEMINI_API_KEY=your-key-here`
- [ ] V1 backend running at port 8000

---

## V2 Definition of Done ✅

- [ ] FAISS index built from ≥ 5 knowledge documents
- [ ] Any alert with risk > 60 returns a Gemini-grounded explanation with source citations
- [ ] `/copilot/chat` handles 5-turn conversations
- [ ] Copilot UI live at `localhost:3000/copilot`
- [ ] Every alert card has "Ask AI about this alert" button
- [ ] Fallback to LIME-only when Gemini API is unavailable
- [ ] All responses cached (no duplicate API calls for same alert)
- [ ] No hardcoded API keys committed to git

---

## Build Order (Start → Finish)

```
1. Seed knowledge documents  (rag/docs/*.txt)
2. chunker.py                (split into 512-token chunks)
3. build_index.py            (embed + FAISS index)
4. retriever.py              (KnowledgeRetriever class)
5. prompts.py                (system prompt templates)
6. alert_chain.py            (Gemini + retriever + response)
7. conversational_chain.py   (multi-turn history manager)
8. copilot.py router         (FastAPI endpoint)
9. Wire into backend/main.py
10. CopilotChat.tsx           (frontend chat UI)
11. SourcePanel.tsx           (citations sidebar)
12. copilot/page.tsx          (full page + routing)
13. Add "Ask AI" button to AlertFeed.tsx
14. End-to-end test
```
