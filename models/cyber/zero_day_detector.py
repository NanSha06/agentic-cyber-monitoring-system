"""
models/cyber/zero_day_detector.py
Autoencoder-based zero-day / unknown attack detector.
Anomaly score = MSE reconstruction error.
Threshold at 95th percentile of normal-traffic reconstruction errors.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
import joblib

FEATURES = [
    "packet_entropy", "auth_failure_burst_rate", "lateral_move_indicator",
]
MODEL_PATH     = "models/cyber/zero_day_detector_v1.keras"
THRESHOLD_PATH = "models/cyber/zero_day_threshold_v1.joblib"


def build_autoencoder(input_dim: int):
    import tensorflow as tf
    from tensorflow.keras import layers

    enc_in    = tf.keras.Input(shape=(input_dim,))
    encoded   = layers.Dense(64, activation="relu")(enc_in)
    encoded   = layers.Dense(32, activation="relu")(encoded)
    bottleneck = layers.Dense(16, activation="relu")(encoded)
    decoded   = layers.Dense(32, activation="relu")(bottleneck)
    decoded   = layers.Dense(64, activation="relu")(decoded)
    output    = layers.Dense(input_dim, activation="linear")(decoded)
    model     = tf.keras.Model(enc_in, output)
    model.compile(optimizer="adam", loss="mse")
    return model


def train(df: pd.DataFrame):
    import tensorflow as tf

    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0

    # Train only on normal traffic to learn baseline
    normal = df[df["threat_type"] == "normal"] if "threat_type" in df.columns else df
    if len(normal) < 100:
        normal = df

    X = normal[FEATURES].fillna(0).astype("float32").values
    model = build_autoencoder(X.shape[1])
    model.fit(X, X, epochs=20, batch_size=256, validation_split=0.1, verbose=1,
              callbacks=[
                  tf.keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True)
              ])

    # Compute threshold at 95th percentile of reconstruction errors
    recon  = model.predict(X, verbose=0)
    errors = np.mean((X - recon) ** 2, axis=1)
    threshold = float(np.percentile(errors, 95))
    print(f"  Zero-day threshold (95th pct): {threshold:.6f}")

    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_PATH)
    joblib.dump(threshold, THRESHOLD_PATH)
    print(f"  💾 Saved → {MODEL_PATH}")
    return model, threshold


def load():
    import tensorflow as tf
    model     = tf.keras.models.load_model(MODEL_PATH)
    threshold = joblib.load(THRESHOLD_PATH)
    return model, threshold


def predict(model, threshold: float, features: dict) -> dict:
    X = np.array([[features.get(f, 0.0) for f in FEATURES]], dtype="float32")
    recon = model.predict(X, verbose=0)
    error = float(np.mean((X - recon) ** 2))
    return {
        "is_zero_day": error > threshold,
        "reconstruction_error": error,
        "threshold": threshold,
    }
