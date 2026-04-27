# 🛡️ Implementation Plan — Agentic Cyber-Battery Intelligence Platform

> **Version:** V1.0 | **Total Duration:** 20 Weeks | **Releases:** V1 → V4  
> **Stack:** Python · FastAPI · Next.js · LangChain · FAISS · Gemini · TimeGAN · CTGAN · MCP  

---

## Table of Contents

1. [Overview & Release Strategy](#1-overview--release-strategy)
2. [V1 — Foundation (Weeks 1–6)](#2-v1--foundation-weeks-16)
3. [V2 — Intelligence (Weeks 7–10)](#3-v2--intelligence-weeks-710)
4. [V3 — Autonomy (Weeks 11–16)](#4-v3--autonomy-weeks-1116)
5. [V4 — Simulation (Weeks 17–20)](#5-v4--simulation-weeks-1720)
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)
7. [Environment Setup](#7-environment-setup)
8. [Definition of Done](#8-definition-of-done)
9. [Risk Register](#9-risk-register)
10. [Folder Structure Reference](#10-folder-structure-reference)

---

## 1. Overview & Release Strategy

Each release is **independently deployable and demonstrable**. You do not need V2 complete to show V1. This is intentional — each version is a portfolio milestone.

```
V1 ──► V2 ──► V3 ──► V4
Data    RAG    MCP    GAN
Models  Copilot Agents Simulation
UI      Search  Audit  Retrain
```

### Release Summary

| Release | Theme | Duration | Primary Deliverable |
|---------|-------|----------|---------------------|
| **V1** | Foundation | Weeks 1–6 | Working ML pipeline + risk dashboard |
| **V2** | Intelligence | Weeks 7–10 | RAG knowledge layer + AI copilot |
| **V3** | Autonomy | Weeks 11–16 | 5-agent system + 4 MCP servers |
| **V4** | Simulation | Weeks 17–20 | GAN rare-event engine + MLOps retraining |

### Principles

- **One working demo per release** — never be in a state where nothing runs
- **Test-first on critical paths** — models, agents, MCP actions
- **Document as you build** — ADRs for every architectural decision
- **No hardcoded secrets** — `.env` from day one

---

## 2. V1 — Foundation (Weeks 1–6)

**Goal:** End-to-end pipeline from raw datasets to live risk dashboard. Every model trained, every chart rendering, LIME explanations visible.

---

### Week 1 — Repository, Datasets & Environment

#### Tasks

- [ ] Initialise monorepo with folder structure (see [Section 10](#10-folder-structure-reference))
- [ ] Set up `pyproject.toml` / `requirements.txt` with pinned versions
- [ ] Configure `.env.example` with all required keys
- [ ] Download and validate all four benchmark datasets

#### Dataset Acquisition

```bash
# Battery datasets
# NASA Battery Aging Dataset
wget https://data.nasa.gov/download/[battery-dataset-url] -O datasets/raw/nasa_battery.zip

# CALCE Lithium-Ion Dataset
# Manual download: https://calce.umd.edu/battery-data
# Save to: datasets/raw/calce/

# Cyber datasets
# CIC-IDS2017 — Canadian Institute for Cybersecurity
# Download: https://www.unb.ca/cic/datasets/ids-2017.html
# Save to: datasets/raw/cic_ids2017/

# UNSW-NB15
# Download: https://research.unsw.edu.au/projects/unsw-nb15-dataset
# Save to: datasets/raw/unsw_nb15/
```

#### Validation Script

```python
# datasets/validate_raw.py
import pandas as pd
from pathlib import Path

EXPECTED = {
    "nasa_battery": ["Voltage_measured", "Current_measured", "Temperature_measured", "Capacity"],
    "cic_ids2017":  ["Flow Duration", "Total Fwd Packets", "Label"],
    "unsw_nb15":    ["dur", "proto", "service", "state", "label"],
}

def validate_dataset(name: str, path: str, required_cols: list[str]):
    df = pd.read_csv(path, nrows=5)
    missing = [c for c in required_cols if c not in df.columns]
    assert not missing, f"{name} missing columns: {missing}"
    print(f"✅ {name} — OK ({Path(path).stat().st_size // 1024} KB)")
```

#### Deliverable
- All datasets present locally, validation script passes with zero errors

---

### Week 2 — Data Engineering Pipeline

#### Tasks

- [ ] Build battery cleaning module
- [ ] Build cyber cleaning module
- [ ] Implement time-alignment logic (sliding window)
- [ ] Define and enforce unified schema
- [ ] Feature engineering — battery, cyber, and fusion features

#### Unified Schema

```python
# preprocessing/schema.py
from dataclasses import dataclass
import pandas as pd

UNIFIED_SCHEMA = {
    "time":             "datetime64[ns]",
    "asset_id":         "object",           # pseudonymised
    "temp":             "float32",          # °C
    "voltage":          "float32",          # V
    "current":          "float32",          # A
    "soc":              "float32",          # State of Charge 0–100
    "soh":              "float32",          # State of Health 0–100
    "threat_type":      "category",         # 'normal', 'ddos', 'bruteforce', etc.
    "auth_failures":    "int32",
    "packet_entropy":   "float32",
    "risk_label":       "int8",             # 0=nominal, 1=warning, 2=critical
}
```

#### Battery Feature Engineering

```python
# preprocessing/features/battery.py

def engineer_battery_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["asset_id", "time"])

    # Rate of temperature change over 10-minute window
    df["temp_rate_of_change"] = (
        df.groupby("asset_id")["temp"]
        .transform(lambda x: x.diff() / x.index.to_series().diff().dt.total_seconds() * 60)
    )

    # Voltage variance over 10-minute rolling window
    df["voltage_variance_10m"] = (
        df.groupby("asset_id")["voltage"]
        .transform(lambda x: x.rolling("10min").var())
    )

    # SOC drop under load
    df["soc_drop_under_load"] = (
        df.groupby("asset_id")["soc"]
        .transform(lambda x: x.diff().clip(upper=0).abs())
    )

    return df
```

#### Cyber Feature Engineering

```python
# preprocessing/features/cyber.py

def engineer_cyber_features(df: pd.DataFrame) -> pd.DataFrame:
    from scipy.stats import entropy
    import numpy as np

    # Packet entropy (proxy from flow stats)
    df["packet_entropy"] = df["packet_size_distribution"].apply(
        lambda x: entropy(x) if x is not None else 0.0
    )

    # Auth failure burst rate — count in 5-min window
    df["auth_failure_burst_rate"] = (
        df.groupby("asset_id")["auth_failures"]
        .transform(lambda x: x.rolling("5min").sum())
    )

    # Lateral movement indicator
    df["lateral_move_indicator"] = (
        (df["unique_dst_ips_10m"] > 5) & (df["auth_failures"] > 0)
    ).astype(int)

    return df
```

#### Fusion Features

```python
# preprocessing/features/fusion.py

def engineer_fusion_features(df: pd.DataFrame) -> pd.DataFrame:
    # Battery drain during active threat window
    is_threat = df["threat_type"] != "normal"
    df["battery_drain_during_alert"] = df["soc_drop_under_load"].where(is_threat, other=0.0)

    # Temperature spike following a network scan event
    scan_times = df[df["threat_type"] == "portscan"]["time"]
    # Tag rows within 15 minutes after a scan
    df["heat_spike_post_scan"] = df.apply(
        lambda row: float(any(
            0 <= (row["time"] - t).total_seconds() <= 900 for t in scan_times
        )),
        axis=1
    )

    # Cross-domain risk delta (15-min rolling change in raw risk proxy)
    df["raw_risk_proxy"] = 0.4 * (100 - df["soh"]) + 0.6 * df["auth_failure_burst_rate"].clip(0, 100)
    df["cross_domain_risk_delta"] = (
        df.groupby("asset_id")["raw_risk_proxy"]
        .transform(lambda x: x.rolling("15min").mean().diff())
    )

    return df
```

#### Deliverable
- `preprocessing/run_pipeline.py` produces `datasets/processed/unified.parquet` without errors
- Schema validated programmatically
- Feature set: ≥ 9 engineered features across battery, cyber, fusion

---

### Week 3 — Model Training: Battery & Cyber

#### Tasks

- [ ] Train SOH Predictor (XGBoost)
- [ ] Train RUL Forecaster (LSTM)
- [ ] Train Battery Anomaly Detector (Isolation Forest)
- [ ] Train Attack Classifier (Random Forest)
- [ ] Train Zero-Day Detector (Autoencoder)
- [ ] Save all models as versioned artifacts

#### SOH Predictor

```python
# models/battery/soh_predictor.py
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib

FEATURES = ["temp", "voltage", "current", "temp_rate_of_change",
            "voltage_variance_10m", "soc_drop_under_load"]
TARGET = "soh"

def train(df):
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    mae = mean_absolute_error(y_test, model.predict(X_test))
    print(f"SOH Predictor MAE: {mae:.3f}")
    assert mae < 5.0, f"MAE {mae} exceeds threshold — check training data"

    joblib.dump(model, "models/battery/soh_predictor_v1.joblib")
    return model
```

#### RUL Forecaster (LSTM)

```python
# models/battery/rul_forecaster.py
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model

SEQ_LEN    = 50     # timesteps per input window
N_FEATURES = 6

def build_model() -> Model:
    inp = tf.keras.Input(shape=(SEQ_LEN, N_FEATURES))
    x   = layers.LSTM(64, return_sequences=True)(inp)
    x   = layers.Dropout(0.2)(x)
    x   = layers.LSTM(64)(x)
    x   = layers.Dropout(0.2)(x)
    x   = layers.Dense(32, activation="relu")(x)
    out = layers.Dense(1, activation="linear", name="rul_cycles")(x)
    return Model(inp, out)

def train(sequences, labels):
    model = build_model()
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse", metrics=["mae"])
    model.fit(sequences, labels, epochs=50, batch_size=64,
              validation_split=0.15, callbacks=[
                  tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True),
                  tf.keras.callbacks.ModelCheckpoint("models/battery/rul_forecaster_v1.keras", save_best_only=True),
              ])
```

#### Attack Classifier

```python
# models/cyber/attack_classifier.py
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib

FEATURES = ["packet_entropy", "auth_failure_burst_rate", "lateral_move_indicator",
            "Flow Duration", "Total Fwd Packets", "Bwd Packet Length Mean"]
TARGET = "threat_type"

def train(df):
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=12,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    print(classification_report(y_test, model.predict(X_test)))
    joblib.dump(model, "models/cyber/attack_classifier_v1.joblib")
    return model
```

#### Autoencoder (Zero-Day)

```python
# models/cyber/zero_day_detector.py
import tensorflow as tf
from tensorflow.keras import layers, Model

def build_autoencoder(input_dim: int) -> Model:
    enc_in = tf.keras.Input(shape=(input_dim,))
    encoded = layers.Dense(64, activation="relu")(enc_in)
    encoded = layers.Dense(32, activation="relu")(encoded)
    bottleneck = layers.Dense(16, activation="relu")(encoded)
    decoded = layers.Dense(32, activation="relu")(bottleneck)
    decoded = layers.Dense(64, activation="relu")(decoded)
    output = layers.Dense(input_dim, activation="linear")(decoded)
    return Model(enc_in, output)

# Anomaly score = MSE reconstruction error
# Threshold set at 95th percentile of normal-traffic reconstruction errors
```

#### Deliverable
- All 5 models trained, saved to `models/` with version suffix
- Evaluation report printed per model
- Attack Classifier recall on critical classes ≥ 85% (pre-GAN augmentation)

---

### Week 4 — Fusion Risk Model & LIME Explainability

#### Tasks

- [ ] Build fusion risk scoring function
- [ ] Implement LIME wrapper for all models
- [ ] Write explanation formatter (human-readable output)
- [ ] Unit-test explanation coverage on 100 sample alerts

#### Fusion Risk Score

```python
# models/fusion/risk_scorer.py
from dataclasses import dataclass

@dataclass
class RiskComponents:
    battery_risk: float   # 0–100
    threat_score: float   # 0–100
    fusion_context: float # 0–100
    temporal_trend: float # -100 to +100 (negative = improving)

WEIGHTS = {
    "battery_risk":    0.35,
    "threat_score":    0.35,
    "fusion_context":  0.20,
    "temporal_trend":  0.10,
}

def compute_risk_score(components: RiskComponents) -> float:
    raw = (
        WEIGHTS["battery_risk"]   * components.battery_risk +
        WEIGHTS["threat_score"]   * components.threat_score +
        WEIGHTS["fusion_context"] * components.fusion_context +
        WEIGHTS["temporal_trend"] * max(0, components.temporal_trend)
    )
    return round(min(max(raw, 0), 100), 2)

def get_risk_tier(score: float) -> dict:
    if score <= 30:
        return {"tier": "NOMINAL",     "color": "green",  "sla": "monitor",    "action": "log"}
    elif score <= 60:
        return {"tier": "INVESTIGATE", "color": "yellow", "sla": "30min",      "action": "flag"}
    elif score <= 80:
        return {"tier": "URGENT",      "color": "orange", "sla": "5min",       "action": "diagnose"}
    else:
        return {"tier": "CRITICAL",    "color": "red",    "sla": "immediate",  "action": "full_pipeline"}
```

#### LIME Wrapper

```python
# explainability/lime_explainer.py
import lime
import lime.lime_tabular
import numpy as np
from typing import Any

class FusionExplainer:
    def __init__(self, model, feature_names: list[str], training_data: np.ndarray):
        self.model = model
        self.explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=training_data,
            feature_names=feature_names,
            mode="regression",
            random_state=42,
        )

    def explain(self, instance: np.ndarray, num_features: int = 6) -> dict:
        exp = self.explainer.explain_instance(
            instance,
            self.model.predict,
            num_features=num_features,
        )
        contributions = exp.as_list()
        return {
            "contributions": [
                {"feature": name, "weight": round(weight, 3)}
                for name, weight in sorted(contributions, key=lambda x: abs(x[1]), reverse=True)
            ],
            "prediction": exp.predicted_value,
            "intercept": exp.intercept[0],
        }

    def format_human_readable(self, explanation: dict, risk_score: float, asset_id: str) -> str:
        lines = [f"ALERT — {asset_id} — Risk Score: {risk_score}/100", "Contributing factors:"]
        for c in explanation["contributions"]:
            sign = "+" if c["weight"] > 0 else ""
            lines.append(f"  · {c['feature']}: {sign}{c['weight']}")
        return "\n".join(lines)
```

#### Deliverable
- `explainability/lime_explainer.py` produces formatted explanation for any alert with risk > 60
- 100% of test alerts with risk > 60 have an attached explanation — assertion in CI

---

### Week 5 — FastAPI Backend

#### Tasks

- [ ] Bootstrap FastAPI application with router structure
- [ ] Implement `/predict` endpoint (batch and single-asset)
- [ ] Implement `/explain` endpoint
- [ ] Implement `/assets` and `/alerts` endpoints
- [ ] WebSocket endpoint for live risk score streaming
- [ ] Basic auth middleware (JWT)

#### Router Structure

```
backend/
  main.py
  routers/
    assets.py        # GET /assets, GET /assets/{id}
    predictions.py   # POST /predict, GET /predictions/history
    alerts.py        # GET /alerts, GET /alerts/{id}
    explanations.py  # GET /explain/{alert_id}
    health.py        # GET /health, GET /metrics
  ws/
    risk_stream.py   # WS /ws/risk-stream
  middleware/
    auth.py
    logging.py
```

#### Example Predict Endpoint

```python
# backend/routers/predictions.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from models.fusion.risk_scorer import compute_risk_score, get_risk_tier, RiskComponents

router = APIRouter(prefix="/predict", tags=["predictions"])

class PredictRequest(BaseModel):
    asset_id: str
    features: dict[str, float]

class PredictResponse(BaseModel):
    asset_id: str
    risk_score: float
    risk_tier: str
    soh: float
    rul_cycles: int
    threat_type: str
    explanation_available: bool

@router.post("/", response_model=PredictResponse)
async def predict(req: PredictRequest):
    # Run all models on features dict
    # ...
    components = RiskComponents(
        battery_risk=battery_risk,
        threat_score=threat_score,
        fusion_context=fusion_context,
        temporal_trend=temporal_trend,
    )
    score = compute_risk_score(components)
    tier  = get_risk_tier(score)
    return PredictResponse(
        asset_id=req.asset_id,
        risk_score=score,
        risk_tier=tier["tier"],
        soh=soh,
        rul_cycles=rul,
        threat_type=threat_type,
        explanation_available=(score > 60),
    )
```

#### Deliverable
- `uvicorn backend.main:app` starts without errors
- All endpoints return correct schemas
- WebSocket streams risk updates at 1Hz for connected clients

---

### Week 6 — Next.js Dashboard (V1 UI)

#### Tasks

- [ ] Bootstrap Next.js 14 app with Tailwind CSS and TypeScript
- [ ] Command Center page — fleet overview, risk gauges, threat heatmap
- [ ] Asset Detail page — battery time-series, security event log, RUL chart
- [ ] Explainability page — LIME bar charts per alert
- [ ] WebSocket integration for live updates

#### Page Structure

```
frontend/
  app/
    page.tsx                # → Command Center
    assets/[id]/page.tsx    # → Asset Detail
    explain/[alertId]/page.tsx
    copilot/page.tsx        # V2
    audit/page.tsx          # V3
  components/
    RiskGauge.tsx
    ThreatHeatmap.tsx
    BatteryChart.tsx
    LimeBarChart.tsx
    AssetTable.tsx
    AlertFeed.tsx
  lib/
    api.ts                  # typed API client
    ws.ts                   # WebSocket hook
```

#### Risk Gauge Component (Example)

```tsx
// components/RiskGauge.tsx
"use client";
import { useEffect, useState } from "react";

interface Props { assetId: string; initialScore: number; }

export function RiskGauge({ assetId, initialScore }: Props) {
  const [score, setScore] = useState(initialScore);

  const color = score <= 30 ? "#22c55e"
    : score <= 60 ? "#eab308"
    : score <= 80 ? "#f97316"
    : "#ef4444";

  const tier = score <= 30 ? "NOMINAL"
    : score <= 60 ? "INVESTIGATE"
    : score <= 80 ? "URGENT"
    : "CRITICAL";

  return (
    <div className="flex flex-col items-center gap-2 p-4 rounded-xl border bg-white shadow-sm">
      <div className="text-sm font-medium text-gray-500">{assetId}</div>
      <div className="text-5xl font-bold" style={{ color }}>{score}</div>
      <div className="text-xs font-semibold tracking-widest px-3 py-1 rounded-full"
           style={{ background: color + "22", color }}>
        {tier}
      </div>
    </div>
  );
}
```

#### V1 Deliverable ✅
- Dashboard runs at `localhost:3000` with real data from FastAPI
- All models predicting, all charts rendering
- LIME explanations visible for any alert with risk > 60
- End-to-end demo flow documented

---

## 3. V2 — Intelligence (Weeks 7–10)

**Goal:** Add RAG knowledge grounding and conversational AI copilot. Every alert links to retrieved incident context and SOP guidance.

---

### Week 7 — Document Corpus & Vector Store

#### Tasks

- [ ] Collect and preprocess knowledge documents
- [ ] Chunk documents with overlap strategy
- [ ] Generate embeddings using HuggingFace sentence-transformers
- [ ] Index into FAISS vector store
- [ ] Build retrieval function with top-k configurable

#### Document Chunking

```python
# rag/ingestion/chunker.py
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path

CHUNK_SIZE    = 512   # tokens
CHUNK_OVERLAP = 64    # tokens

def chunk_documents(doc_dir: str) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = []
    for path in Path(doc_dir).rglob("*.txt"):
        text = path.read_text(encoding="utf-8")
        docs = splitter.create_documents([text], metadatas=[{"source": str(path)}])
        chunks.extend(docs)
    return chunks
```

#### FAISS Index Builder

```python
# rag/ingestion/build_index.py
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def build_faiss_index(chunks: list, index_path: str = "rag/index/faiss_store"):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    store = FAISS.from_documents(chunks, embeddings)
    store.save_local(index_path)
    print(f"✅ FAISS index built — {len(chunks)} chunks indexed at {index_path}")
    return store
```

#### Retrieval Function

```python
# rag/retrieval/retriever.py
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

class KnowledgeRetriever:
    def __init__(self, index_path: str = "rag/index/faiss_store"):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.store = FAISS.load_local(index_path, self.embeddings,
                                      allow_dangerous_deserialization=True)

    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        docs = self.store.similarity_search_with_score(query, k=k)
        return [
            {"content": doc.page_content, "source": doc.metadata["source"],
             "score": round(float(score), 4)}
            for doc, score in docs
        ]
```

#### Deliverable
- FAISS index built and persisted at `rag/index/faiss_store`
- Retrieval function returns top-5 relevant chunks for any alert query
- Index covers: OEM manuals, SOPs, CVEs, incident reports

---

### Week 8 — Gemini Integration & RAG Chain

#### Tasks

- [ ] Set up Gemini API client with retry logic
- [ ] Build LangChain RAG chain (retrieve → inject → generate)
- [ ] Design prompt templates for alert explanation and SOP lookup
- [ ] Add source citation to every RAG response

#### RAG Chain

```python
# rag/chains/alert_chain.py
import google.generativeai as genai
from rag.retrieval.retriever import KnowledgeRetriever

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_PROMPT = """You are an expert systems engineer for cyber-physical asset management.
You have been given:
1. An alert summary with LIME feature contributions
2. Retrieved context from incident reports, OEM manuals, and security advisories

Your task: Explain the root cause in plain English and recommend the top 3 mitigation actions.
Always cite your sources. Never speculate beyond the provided context.
Keep your response to 3 paragraphs maximum."""

class AlertRAGChain:
    def __init__(self):
        self.retriever = KnowledgeRetriever()
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def run(self, alert: dict, lime_explanation: dict) -> dict:
        query = self._build_query(alert, lime_explanation)
        context_docs = self.retriever.retrieve(query, k=5)
        context_text = "\n\n---\n\n".join(
            f"[Source: {d['source']}]\n{d['content']}" for d in context_docs
        )
        prompt = f"{SYSTEM_PROMPT}\n\nALERT:\n{query}\n\nCONTEXT:\n{context_text}"
        response = self.model.generate_content(prompt)
        return {
            "answer": response.text,
            "sources": [d["source"] for d in context_docs],
            "query": query,
        }

    def _build_query(self, alert: dict, lime: dict) -> str:
        contribs = ", ".join(
            f"{c['feature']} ({c['weight']:+.2f})"
            for c in lime["contributions"][:4]
        )
        return (
            f"Asset {alert['asset_id']} — Risk Score {alert['risk_score']}/100. "
            f"Key contributing factors: {contribs}. "
            f"Threat type: {alert.get('threat_type', 'unknown')}. "
            f"What is the likely root cause and recommended mitigation?"
        )
```

#### Deliverable
- RAG chain produces grounded response with source citations for any alert
- Response latency < 8 seconds end-to-end

---

### Week 9 — AI Copilot Backend

#### Tasks

- [ ] Build `/copilot/chat` API endpoint with conversation history
- [ ] Implement intent classification (alert query vs. general query vs. SOP lookup)
- [ ] Wire copilot to live alert data + RAG retrieval
- [ ] Add rate limiting per session

#### Copilot Endpoint

```python
# backend/routers/copilot.py
from fastapi import APIRouter
from pydantic import BaseModel
from rag.chains.alert_chain import AlertRAGChain

router  = APIRouter(prefix="/copilot", tags=["copilot"])
chain   = AlertRAGChain()

class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str

class CopilotRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    asset_context: str | None = None   # e.g. "Tower-12"

class CopilotResponse(BaseModel):
    response: str
    sources: list[str]
    suggested_actions: list[str]

@router.post("/chat", response_model=CopilotResponse)
async def chat(req: CopilotRequest):
    # Resolve asset context if provided
    alert = await get_latest_alert(req.asset_context) if req.asset_context else None
    # Route to RAG chain
    result = chain.run_conversational(req.message, req.history, alert)
    return CopilotResponse(**result)
```

#### Deliverable
- Copilot answers "Why is Tower-12 risky?" with cited, grounded response
- Handles 5-turn conversation with history context

---

### Week 10 — AI Copilot UI & V2 Polish

#### Tasks

- [ ] Build Copilot page in Next.js (chat interface, suggested prompts)
- [ ] Link alerts in Command Center to Copilot with pre-filled context
- [ ] Source citation panel in Copilot UI
- [ ] V2 end-to-end demo flow recorded and documented

#### V2 Deliverable ✅
- Full RAG-powered copilot running in browser
- Every alert linkable to copilot with "Ask AI about this alert" button
- Sources displayed with document name and relevance score

---

## 4. V3 — Autonomy (Weeks 11–16)

**Goal:** Five-agent autonomous system with four MCP servers. Every action logged, every destructive action gated by Compliance Agent.

---

### Week 11 — Agent Framework Setup

#### Tasks

- [ ] Define base `Agent` abstract class with input/output schemas
- [ ] Implement message bus (Redis pub/sub) for inter-agent communication
- [ ] Set up agent orchestrator with event-driven trigger logic
- [ ] Write agent unit test harness

#### Base Agent

```python
# agents/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from datetime import datetime

class AgentInput(BaseModel):
    event_id: str
    timestamp: datetime
    payload: dict

class AgentOutput(BaseModel):
    event_id: str
    agent_name: str
    status: str        # "success" | "escalated" | "blocked"
    result: dict
    next_agent: str | None = None

class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput:
        ...

    async def emit(self, output: AgentOutput, bus):
        await bus.publish(f"agent:{output.next_agent}", output.json())
```

---

### Weeks 12–13 — Five Agent Implementations

#### Monitoring Agent

```python
# agents/monitoring_agent.py
class MonitoringAgent(BaseAgent):
    name = "monitoring"

    async def run(self, input: AgentInput) -> AgentOutput:
        risk_score = input.payload["risk_score"]
        tier = get_risk_tier(risk_score)

        if tier["tier"] in ("URGENT", "CRITICAL"):
            return AgentOutput(
                event_id=input.event_id, agent_name=self.name,
                status="success",
                result={"tier": tier["tier"], "risk_score": risk_score},
                next_agent="diagnosis",
            )
        return AgentOutput(event_id=input.event_id, agent_name=self.name,
                           status="success", result={"action": "logged"})
```

#### Diagnosis Agent

```python
# agents/diagnosis_agent.py
class DiagnosisAgent(BaseAgent):
    name = "diagnosis"

    def __init__(self):
        self.rag_chain = AlertRAGChain()
        self.explainer = FusionExplainer(...)

    async def run(self, input: AgentInput) -> AgentOutput:
        lime_exp = self.explainer.explain(input.payload["feature_vector"])
        rag_resp = self.rag_chain.run(input.payload["alert"], lime_exp)
        return AgentOutput(
            event_id=input.event_id, agent_name=self.name,
            status="success",
            result={"lime": lime_exp, "rag_analysis": rag_resp, "causal_chain": rag_resp["answer"]},
            next_agent="recommendation",
        )
```

#### Recommendation Agent

```python
# agents/recommendation_agent.py
RESPONSE_TEMPLATES = {
    "CRITICAL": [
        "Immediately isolate {asset_id} from the network via Cyber MCP quarantine_asset()",
        "Dispatch maintenance team for thermal inspection within 15 minutes",
        "Activate backup power routing for dependent downstream assets",
    ],
    "URGENT": [
        "Increase monitoring frequency for {asset_id} to 5-second polling",
        "Block suspicious source IPs via Cyber MCP block_ip()",
        "Alert asset owner and security team via notification workflow",
    ],
}

class RecommendationAgent(BaseAgent):
    name = "recommendation"

    async def run(self, input: AgentInput) -> AgentOutput:
        tier = input.payload["tier"]
        asset_id = input.payload["asset_id"]
        actions = [a.format(asset_id=asset_id) for a in RESPONSE_TEMPLATES.get(tier, [])]
        return AgentOutput(
            event_id=input.event_id, agent_name=self.name,
            status="success",
            result={"proposed_actions": actions, "requires_approval": tier == "CRITICAL"},
            next_agent="compliance",
        )
```

#### Compliance Agent

```python
# agents/compliance_agent.py
BLOCKED_ACTIONS_WITHOUT_APPROVAL = ["quarantine_asset", "block_ip", "shutdown"]

class ComplianceAgent(BaseAgent):
    name = "compliance"

    async def run(self, input: AgentInput) -> AgentOutput:
        actions = input.payload["proposed_actions"]
        blocked, approved = [], []

        for action in actions:
            requires_human = any(b in action for b in BLOCKED_ACTIONS_WITHOUT_APPROVAL)
            if requires_human and not input.payload.get("human_approved"):
                blocked.append({"action": action, "reason": "requires_human_approval"})
            else:
                approved.append(action)

        return AgentOutput(
            event_id=input.event_id, agent_name=self.name,
            status="escalated" if blocked else "success",
            result={"approved": approved, "blocked": blocked},
            next_agent="reporting",
        )
```

#### Reporting Agent

```python
# agents/reporting_agent.py
class ReportingAgent(BaseAgent):
    name = "reporting"

    async def run(self, input: AgentInput) -> AgentOutput:
        report = {
            "event_id":     input.event_id,
            "asset_id":     input.payload["asset_id"],
            "risk_score":   input.payload["risk_score"],
            "causal_chain": input.payload["causal_chain"],
            "actions_approved": input.payload["approved"],
            "actions_blocked":  input.payload["blocked"],
            "timestamp":    input.timestamp.isoformat(),
            "status":       "pending_human_review" if input.payload["blocked"] else "resolved",
        }
        await write_audit_log(report)   # via Governance MCP
        return AgentOutput(
            event_id=input.event_id, agent_name=self.name,
            status="success", result={"report_id": report["event_id"]},
        )
```

---

### Week 14 — Four MCP Servers

#### MCP Server Structure

```
mcp_servers/
  battery_mcp/
    server.py        # FastAPI server exposing battery tools
    tools.py         # get_asset_health, get_rul, flag_for_maintenance
  cyber_mcp/
    server.py
    tools.py         # get_active_alerts, quarantine_asset, block_ip
  analytics_mcp/
    server.py
    tools.py         # run_prediction, explain_case, get_feature_importance
  governance_mcp/
    server.py
    tools.py         # write_audit_log, policy_check, get_compliance_status
```

#### Battery MCP Example

```python
# mcp_servers/battery_mcp/tools.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/battery", tags=["battery-mcp"])

class AssetHealthResponse(BaseModel):
    asset_id: str
    soh: float
    soc: float
    temp: float
    status: str       # "healthy" | "degraded" | "critical"
    rul_cycles: int

@router.get("/health/{asset_id}", response_model=AssetHealthResponse)
async def get_asset_health(asset_id: str):
    # Query battery telemetry store
    ...

@router.post("/maintenance/flag/{asset_id}")
async def flag_for_maintenance(asset_id: str, priority: str = "standard"):
    # Write to maintenance queue + audit log
    await write_audit_log({"tool": "flag_for_maintenance", "asset_id": asset_id, "priority": priority})
    ...
```

#### Governance MCP — Audit Log

```python
# mcp_servers/governance_mcp/tools.py
import json
from datetime import datetime, timezone
from pathlib import Path

AUDIT_LOG_PATH = Path("audit_logs/")

async def write_audit_log(entry: dict) -> str:
    AUDIT_LOG_PATH.mkdir(exist_ok=True)
    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
    entry["log_id"]    = f"LOG-{int(datetime.now().timestamp() * 1000)}"
    log_file = AUDIT_LOG_PATH / f"{datetime.now().date()}.jsonl"
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["log_id"]

async def policy_check(action: str, context: dict) -> dict:
    DESTRUCTIVE = {"quarantine_asset", "block_ip", "shutdown_asset"}
    if action in DESTRUCTIVE:
        return {"allowed": False, "reason": "requires_human_authorization", "action": action}
    return {"allowed": True, "action": action}
```

#### Deliverable
- All 4 MCP servers running (ports 8001–8004)
- Each tool call logged in `audit_logs/*.jsonl`
- Destructive actions return `allowed: False` without prior human authorization

---

### Weeks 15–16 — Agent Orchestration, Audit UI & V3 Polish

#### Tasks

- [ ] Wire agent pipeline end-to-end via Redis event bus
- [ ] Build Audit Trail page in Next.js (tool call log, agent timeline)
- [ ] Add human approval flow in UI (approve/reject blocked actions)
- [ ] Integration test: CRITICAL alert → full 5-agent pipeline → audit log entry
- [ ] V3 demo flow recorded

#### V3 Deliverable ✅
- CRITICAL risk event triggers full agent pipeline in < 10 seconds
- Compliance Agent blocks destructive actions; UI prompts operator
- Every action logged in immutable audit trail
- Audit Trail page shows complete event timeline

---

## 5. V4 — Simulation (Weeks 17–20)

**Goal:** GAN rare-event simulator. Synthetic thermal runaway and APT scenarios used to retrain all models. Measurable recall improvement validated.

---

### Weeks 17–18 — TimeGAN (Battery) & CTGAN (Cyber)

#### TimeGAN Setup

```python
# gan/timegan/train.py
# Uses: https://github.com/jsyoon0823/TimeGAN

import numpy as np
from gan.timegan.model import TimeGAN

def train_timegan(sequences: np.ndarray, seq_len: int = 50, n_features: int = 6):
    """
    sequences: shape (N, seq_len, n_features)
    Target: thermal runaway precursor trajectories
    """
    model = TimeGAN(
        hidden_dim=24,
        num_layers=3,
        iterations=5000,
        batch_size=128,
        learning_rate=1e-3,
        seq_len=seq_len,
        n_features=n_features,
    )
    model.fit(sequences)
    model.save("gan/timegan/checkpoints/thermal_runaway_v1")
    return model

def generate_synthetic_battery(model, n_samples: int = 1000) -> np.ndarray:
    synthetic = model.generate(n_samples)
    # Validate: distribution parity test against real sequences
    from gan.validation.discriminative_score import discriminative_score
    score = discriminative_score(real=sequences, synthetic=synthetic)
    print(f"TimeGAN discriminative score: {score:.4f}  (target < 0.15)")
    assert score < 0.15, "Synthetic data fails quality threshold"
    return synthetic
```

#### CTGAN Setup

```python
# gan/ctgan/train.py
from ctgan import CTGAN

DISCRETE_COLS = ["threat_type", "protocol", "service", "lateral_move_indicator"]

def train_ctgan(df, epochs: int = 300):
    model = CTGAN(epochs=epochs, verbose=True)
    model.fit(df, discrete_columns=DISCRETE_COLS)
    model.save("gan/ctgan/checkpoints/cyber_tabular_v1")
    return model

def generate_synthetic_cyber(model, n_samples: int = 5000):
    synthetic = model.sample(n_samples)
    # Filter to minority-class attack scenarios only
    attack_mask = synthetic["threat_type"] != "normal"
    return synthetic[attack_mask]
```

---

### Week 19 — Synthetic Data Validation & Model Retraining

#### Validation Suite

```python
# gan/validation/suite.py

def run_validation_suite(real_df, synthetic_df, name: str) -> dict:
    results = {}

    # 1. Feature distribution similarity (KS test per column)
    from scipy.stats import ks_2samp
    ks_scores = {}
    for col in real_df.select_dtypes("number").columns:
        stat, p = ks_2samp(real_df[col].dropna(), synthetic_df[col].dropna())
        ks_scores[col] = {"statistic": round(stat, 4), "p_value": round(p, 4)}
    results["ks_test"] = ks_scores

    # 2. Train-on-synthetic, test-on-real (TSTR)
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import f1_score
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(synthetic_df[FEATURES], synthetic_df[TARGET])
    preds = clf.predict(real_df[FEATURES])
    results["tstr_f1"] = round(f1_score(real_df[TARGET], preds, average="weighted"), 4)

    # 3. Privacy: nearest-neighbour distance ratio (NNDR)
    results["nndr"] = compute_nndr(real_df, synthetic_df)

    print(f"\n=== {name} Validation ===")
    print(f"  TSTR F1:  {results['tstr_f1']}  (target > 0.80)")
    print(f"  NNDR:     {results['nndr']:.4f}  (target > 0.50)")
    return results
```

#### Model Retraining Pipeline

```python
# gan/retrain_pipeline.py
"""
Full retraining pipeline:
1. Load validated synthetic data
2. Merge with real training data (augmented set)
3. Retrain all 5 models
4. Evaluate recall on critical classes (pre vs. post)
5. Promote new models if recall improves by > 5%
"""

def run_retrain_pipeline():
    real    = load_parquet("datasets/processed/unified.parquet")
    syn_bat = np.load("gan/timegan/synthetic_thermal_runaway.npy")
    syn_cyb = pd.read_parquet("gan/ctgan/synthetic_cyber_attacks.parquet")

    augmented = merge_and_balance(real, syn_bat, syn_cyb)

    # Retrain and compare
    results = {}
    for model_fn in [train_soh, train_rul, train_anomaly, train_classifier, train_autoencoder]:
        before, after = model_fn(real), model_fn(augmented)
        results[model_fn.__name__] = {"before": before.recall, "after": after.recall}
        if after.recall > before.recall + 0.05:
            after.save(versioned=True)   # promote new model
            print(f"✅ {model_fn.__name__} promoted: {before.recall:.3f} → {after.recall:.3f}")
```

---

### Week 20 — MLOps, Documentation & Final Polish

#### Tasks

- [ ] Schedule monthly retraining pipeline (cron or Airflow DAG)
- [ ] Write GitHub README (recruiter-grade)
- [ ] Generate architecture diagram as SVG/PNG
- [ ] Record full V4 demo video
- [ ] Write ADRs for key decisions (model choice, MCP design, GAN approach)

#### Automated Retraining Schedule

```yaml
# .github/workflows/monthly_retrain.yml
name: Monthly Model Retraining

on:
  schedule:
    - cron: "0 2 1 * *"    # 02:00 UTC on the 1st of each month
  workflow_dispatch:

jobs:
  retrain:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: python gan/retrain_pipeline.py
      - run: python scripts/promote_models.py
```

#### V4 Deliverable ✅
- GAN simulator generates valid synthetic rare events
- Validation suite passes (TSTR F1 > 0.80, NNDR > 0.50)
- Critical-class recall improves ≥ 5% post-augmentation (documented)
- Monthly retraining runs automatically via CI/CD
- Full portfolio documentation complete

---

## 6. Cross-Cutting Concerns

### Testing Strategy

| Layer | Test Type | Tool | Coverage Target |
|-------|-----------|------|-----------------|
| Data pipeline | Unit | pytest | 100% feature functions |
| Models | Integration | pytest | All models train + predict |
| API endpoints | Integration | pytest + httpx | All routes, edge cases |
| Agents | Unit + Integration | pytest | Each agent independently + full pipeline |
| MCP servers | Contract tests | pytest | Every tool call + audit log entry |
| UI | E2E | Playwright | Command Center + Copilot + Audit pages |

### Logging & Observability

```python
# backend/middleware/logging.py
import structlog

log = structlog.get_logger()

# Log every prediction with latency
log.info("prediction", asset_id=asset_id, risk_score=score,
         tier=tier, latency_ms=latency, model_version="v1")

# Log every agent action
log.info("agent_action", agent=agent_name, event_id=event_id,
         status=status, next_agent=next_agent)

# Log every MCP tool call
log.info("mcp_tool_call", server="battery_mcp", tool="get_asset_health",
         asset_id=asset_id, latency_ms=latency, log_id=log_id)
```

### Secret Management

```bash
# .env.example  (commit this)
GEMINI_API_KEY=
JWT_SECRET=
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:pass@localhost:5432/platform
BATTERY_MCP_URL=http://localhost:8001
CYBER_MCP_URL=http://localhost:8002
ANALYTICS_MCP_URL=http://localhost:8003
GOVERNANCE_MCP_URL=http://localhost:8004

# .env  (never commit — add to .gitignore)
```

---

## 7. Environment Setup

### Python Environment

```bash
# Prerequisites: Python 3.11+, Node.js 20+, Redis, PostgreSQL

# 1. Clone repo
git clone https://github.com/your-org/cyber-battery-platform.git
cd cyber-battery-platform

# 2. Python environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Environment variables
cp .env.example .env
# Fill in GEMINI_API_KEY and other secrets

# 4. Validate datasets
python datasets/validate_raw.py

# 5. Run preprocessing pipeline
python preprocessing/run_pipeline.py

# 6. Train all models
python models/train_all.py

# 7. Start services
redis-server &
uvicorn backend.main:app --reload --port 8000 &
uvicorn mcp_servers.battery_mcp.server:app --port 8001 &
uvicorn mcp_servers.cyber_mcp.server:app --port 8002 &
uvicorn mcp_servers.analytics_mcp.server:app --port 8003 &
uvicorn mcp_servers.governance_mcp.server:app --port 8004 &

# 8. Start frontend
cd frontend && npm install && npm run dev
```

### Python Dependencies (Core)

```txt
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
xgboost==2.0.3
scikit-learn==1.5.0
tensorflow==2.16.0
pandas==2.2.2
numpy==1.26.4
langchain==0.2.0
langchain-community==0.2.0
faiss-cpu==1.8.0
sentence-transformers==3.0.0
google-generativeai==0.7.0
ctgan==0.9.0
lime==0.2.0.1
structlog==24.1.0
redis==5.0.4
pytest==8.2.0
httpx==0.27.0
```

---

## 8. Definition of Done

A feature or release is **Done** when ALL of the following are true:

- [ ] Code reviewed and merged to `main` via pull request
- [ ] Unit tests written and passing (no skips on critical paths)
- [ ] API endpoints return correct response schemas
- [ ] New functionality covered by at least one integration test
- [ ] Every MCP tool call appears in `audit_logs/`
- [ ] Every alert with risk > 60 has an attached LIME explanation
- [ ] No hardcoded secrets or API keys in committed code
- [ ] Feature branch deleted after merge
- [ ] Release demo run successfully (end-to-end, no mocked data)

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CALCE/NASA datasets have schema changes | Low | High | Pin exact dataset versions; validate on load |
| Gemini API rate limits hit in demo | Medium | Medium | Implement exponential backoff + cache common queries |
| TimeGAN training too slow on CPU | High | Medium | Use Google Colab GPU for GAN training; save checkpoint |
| FAISS index rebuild on every restart | Low | Low | Persist index to disk; only rebuild on new docs |
| Agent infinite loop (no termination) | Medium | High | Max-hop limit (n=7) on agent pipeline; timeout per agent |
| MCP server down during demo | Low | High | Health check endpoint; fallback mock mode for demo |
| Synthetic data fails privacy threshold | Medium | Medium | NNDR check gates promotion; do not use if NNDR < 0.50 |
| Alert fatigue from noisy model | Medium | High | Calibrate threshold on validation set; target ≤ 5 false alarms/hour |

---

## 10. Folder Structure Reference

```
project/
│
├── frontend/                        # Next.js 14, TypeScript, Tailwind
│   ├── app/
│   │   ├── page.tsx                 # Command Center
│   │   ├── assets/[id]/page.tsx    # Asset Detail
│   │   ├── explain/[id]/page.tsx   # LIME Explainability
│   │   ├── copilot/page.tsx        # AI Copilot (V2)
│   │   └── audit/page.tsx          # MCP Audit Trail (V3)
│   └── components/
│
├── backend/                         # FastAPI, Python 3.11
│   ├── main.py
│   ├── routers/
│   └── ws/
│
├── datasets/
│   ├── raw/                         # Original downloaded datasets
│   └── processed/                   # unified.parquet, augmented.parquet
│
├── preprocessing/
│   ├── run_pipeline.py
│   ├── cleaning/
│   └── features/                    # battery.py, cyber.py, fusion.py
│
├── models/
│   ├── train_all.py
│   ├── battery/                     # soh_predictor, rul_forecaster, anomaly_detector
│   ├── cyber/                       # attack_classifier, zero_day_detector
│   └── fusion/                      # risk_scorer.py
│
├── gan/
│   ├── timegan/                     # TimeGAN training + checkpoints
│   ├── ctgan/                       # CTGAN training + checkpoints
│   ├── validation/                  # discriminative_score, ks_test, nndr
│   └── retrain_pipeline.py
│
├── rag/
│   ├── ingestion/                   # chunker.py, build_index.py
│   ├── retrieval/                   # retriever.py
│   ├── chains/                      # alert_chain.py
│   └── index/                       # FAISS persisted store (gitignored)
│
├── agents/
│   ├── base.py
│   ├── monitoring_agent.py
│   ├── diagnosis_agent.py
│   ├── recommendation_agent.py
│   ├── compliance_agent.py
│   ├── reporting_agent.py
│   └── orchestrator.py
│
├── mcp_servers/
│   ├── battery_mcp/                 # port 8001
│   ├── cyber_mcp/                   # port 8002
│   ├── analytics_mcp/               # port 8003
│   └── governance_mcp/              # port 8004
│
├── explainability/
│   ├── lime_explainer.py
│   └── explanation_store.py
│
├── audit_logs/                      # JSONL audit entries (gitignored)
│
├── docs/
│   ├── adr/                         # Architecture Decision Records
│   ├── architecture.svg
│   └── api_spec.yaml
│
├── .github/workflows/
│   └── monthly_retrain.yml
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

*Last updated: Week 0 — Pre-implementation*  
*Next review: End of V1 (Week 6)*