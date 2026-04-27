"""
models/battery/anomaly_detector.py
Isolation Forest anomaly detector for battery telemetry.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
import joblib

FEATURES = [
    "temp", "voltage", "current",
    "temp_rate_of_change", "voltage_variance_10m", "soc_drop_under_load",
]
MODEL_PATH = "models/battery/anomaly_detector_v1.joblib"


def train(df: pd.DataFrame):
    from sklearn.ensemble import IsolationForest

    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0

    X = df[FEATURES].fillna(0).astype("float32")
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    # Quick evaluation: anomaly rate on training data
    preds = model.predict(X)
    anomaly_rate = (preds == -1).mean()
    print(f"  Battery Anomaly Detector trained — anomaly rate: {anomaly_rate:.3f}")

    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"  💾 Saved → {MODEL_PATH}")
    return model


def load():
    return joblib.load(MODEL_PATH)


def predict(model, features: dict) -> dict:
    """Returns {'is_anomaly': bool, 'score': float}"""
    X = np.array([[features.get(f, 0.0) for f in FEATURES]], dtype="float32")
    pred  = model.predict(X)[0]       # 1=normal, -1=anomaly
    score = float(model.score_samples(X)[0])   # lower = more anomalous
    return {
        "is_anomaly": pred == -1,
        "score": score,
    }
