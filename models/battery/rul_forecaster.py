"""
models/battery/rul_forecaster.py
LSTM-based Remaining Useful Life (RUL) forecaster.
"""
from __future__ import annotations
import numpy as np
from pathlib import Path

SEQ_LEN    = 50
N_FEATURES = 6
MODEL_PATH = "models/battery/rul_forecaster_v1.keras"

FEATURES = [
    "temp", "voltage", "current",
    "temp_rate_of_change", "voltage_variance_10m", "soc_drop_under_load",
]


def build_model():
    import tensorflow as tf
    from tensorflow.keras import layers

    inp = tf.keras.Input(shape=(SEQ_LEN, N_FEATURES))
    x   = layers.LSTM(64, return_sequences=True)(inp)
    x   = layers.Dropout(0.2)(x)
    x   = layers.LSTM(64)(x)
    x   = layers.Dropout(0.2)(x)
    x   = layers.Dense(32, activation="relu")(x)
    out = layers.Dense(1, activation="linear", name="rul_cycles")(x)
    model = tf.keras.Model(inp, out)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="mse",
        metrics=["mae"],
    )
    return model


def make_sequences(df, seq_len: int = SEQ_LEN):
    """Convert time-series dataframe into (sequences, labels) numpy arrays."""
    import pandas as pd
    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0

    seqs, labels = [], []
    for asset_id, grp in df.groupby("asset_id"):
        vals = grp[FEATURES].fillna(0).astype("float32").values
        # RUL label = remaining rows (proxy for cycle life)
        n = len(vals)
        for i in range(n - seq_len):
            seqs.append(vals[i:i + seq_len])
            labels.append(float(n - i - seq_len))

    return np.array(seqs, dtype="float32"), np.array(labels, dtype="float32")


def train(df):
    import tensorflow as tf

    sequences, labels = make_sequences(df)
    if len(sequences) < 100:
        print("  ⚠️  Not enough data for LSTM training — skipping")
        return None

    model = build_model()
    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    model.fit(
        sequences, labels,
        epochs=30,
        batch_size=64,
        validation_split=0.15,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
            tf.keras.callbacks.ModelCheckpoint(MODEL_PATH, save_best_only=True),
        ],
        verbose=1,
    )
    print(f"  💾 Saved → {MODEL_PATH}")
    return model


def load():
    import tensorflow as tf
    return tf.keras.models.load_model(MODEL_PATH)


def predict(model, recent_window: np.ndarray) -> int:
    """recent_window: shape (SEQ_LEN, N_FEATURES)"""
    X = recent_window[np.newaxis, :, :].astype("float32")
    return max(0, int(model.predict(X, verbose=0)[0][0]))
