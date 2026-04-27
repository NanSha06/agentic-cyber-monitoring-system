# 🛡️ Agentic Cyber-Battery Intelligence Platform

> ML-powered risk intelligence for cyber-physical battery assets — V1 Foundation

## Architecture

```
Battery Telemetry + Cyber Network Logs
           ↓
   Data Pipeline (preprocessing/)
           ↓
   5 ML Models (models/)
   ├── SOH Predictor (XGBoost)
   ├── RUL Forecaster (LSTM)
   ├── Battery Anomaly Detector (IsolationForest)
   ├── Attack Classifier (RandomForest)
   └── Zero-Day Detector (Autoencoder)
           ↓
   Fusion Risk Scorer + LIME Explainability
           ↓
   FastAPI Backend (port 8000)
           ↓
   Next.js 14 Dashboard (port 3000)
```

## Quick Start

### 1. Python Environment

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env
```

### 2. Extract Datasets

```bash
python scripts/extract_datasets.py
```

### 3. Run Preprocessing Pipeline

```bash
python preprocessing/run_pipeline.py
```

### 4. Train All Models

```bash
python models/train_all.py
# Or skip LSTM/TF models on CPU:
python models/train_all.py --skip-tf
```

### 5. Start Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

API Docs: http://localhost:8000/docs

### 6. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

## Datasets

| Dataset | Domain | Source |
|---------|--------|--------|
| NASA Battery Aging | Battery | `5. Battery Data Set.zip` |
| CIC-IDS2017 | Cyber | `cicids/*.zip` |

## Release Roadmap

| Release | Feature | Status |
|---------|---------|--------|
| **V1** | ML pipeline + risk dashboard | ✅ Foundation built |
| **V2** | RAG + AI Copilot | 🔜 Week 7–10 |
| **V3** | 5-Agent system + MCP | 🔜 Week 11–16 |
| **V4** | GAN + MLOps | 🔜 Week 17–20 |
