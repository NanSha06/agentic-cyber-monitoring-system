"""
models/battery/soh_predictor.py
XGBoost State-of-Health (SOH) regression model.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
import joblib

FEATURES = [
    "temp", "voltage", "current",
    "temp_rate_of_change", "voltage_variance_10m", "soc_drop_under_load",
]
TARGET = "soh"
MODEL_PATH = "models/battery/soh_predictor_v1.joblib"


def _fill_features(df: pd.DataFrame) -> pd.DataFrame:
    """Fill any missing engineered feature columns with 0."""
    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0
    return df


def train(df: pd.DataFrame):
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error

    df = _fill_features(df.copy())
    df = df.dropna(subset=[TARGET] + FEATURES)

    X, y = df[FEATURES].astype("float32"), df[TARGET].astype("float32")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              verbose=False)

    mae = mean_absolute_error(y_test, model.predict(X_test))
    print(f"  SOH Predictor MAE: {mae:.3f}  (threshold < 5.0)")

    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"  💾 Saved → {MODEL_PATH}")
    return model


def load() -> object:
    return joblib.load(MODEL_PATH)


def predict(model, features: dict) -> float:
    import numpy as np
    X = np.array([[features.get(f, 0.0) for f in FEATURES]], dtype="float32")
    return float(model.predict(X)[0])
