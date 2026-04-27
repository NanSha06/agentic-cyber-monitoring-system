"""
models/cyber/attack_classifier.py
Random Forest multi-class attack classifier on CIC-IDS2017 features.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
import joblib

FEATURES = [
    "packet_entropy", "auth_failure_burst_rate", "lateral_move_indicator",
]
TARGET    = "threat_type"
MODEL_PATH = "models/cyber/attack_classifier_v1.joblib"
ENCODER_PATH = "models/cyber/attack_classifier_encoder_v1.joblib"


def train(df: pd.DataFrame):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    from sklearn.preprocessing import LabelEncoder

    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0

    df = df.dropna(subset=FEATURES + [TARGET])
    X = df[FEATURES].astype("float32")
    le = LabelEncoder()
    y  = le.fit_transform(df[TARGET].astype(str))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    print(classification_report(y_test, model.predict(X_test),
                                target_names=le.classes_))

    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)
    print(f"  💾 Saved → {MODEL_PATH}")
    return model, le


def load():
    return joblib.load(MODEL_PATH), joblib.load(ENCODER_PATH)


def predict(model, le, features: dict) -> dict:
    X = np.array([[features.get(f, 0.0) for f in FEATURES]], dtype="float32")
    pred_idx = model.predict(X)[0]
    proba    = model.predict_proba(X)[0]
    return {
        "threat_type": le.inverse_transform([pred_idx])[0],
        "confidence":  float(proba.max()),
        "probabilities": {cls: float(p) for cls, p in zip(le.classes_, proba)},
    }
