"""
explainability/lime_explainer.py
LIME wrapper for explaining any model prediction in the platform.
"""
from __future__ import annotations
from typing import Callable
import numpy as np


class FusionExplainer:
    def __init__(
        self,
        model: object,
        feature_names: list[str],
        training_data: np.ndarray,
        mode: str = "regression",
    ):
        import lime.lime_tabular

        self.model = model
        self.feature_names = feature_names
        self.explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=training_data,
            feature_names=feature_names,
            mode=mode,
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
                {"feature": name, "weight": round(float(weight), 3)}
                for name, weight in sorted(contributions,
                                           key=lambda x: abs(x[1]),
                                           reverse=True)
            ],
            "prediction": float(exp.predicted_value),
            "intercept":  float(exp.intercept[0]) if hasattr(exp, "intercept") else 0.0,
        }

    def format_human_readable(
        self,
        explanation: dict,
        risk_score: float,
        asset_id: str,
    ) -> str:
        lines = [
            f"ALERT — {asset_id} — Risk Score: {risk_score}/100",
            "Contributing factors:",
        ]
        for c in explanation["contributions"]:
            sign = "+" if c["weight"] > 0 else ""
            lines.append(f"  · {c['feature']}: {sign}{c['weight']}")
        return "\n".join(lines)


# ── Standalone explanation function for API use ────────────────────────────────

def explain_prediction(
    model,
    instance_features: dict,
    feature_names: list[str],
    training_data: np.ndarray,
    num_features: int = 6,
) -> dict:
    """Convenience wrapper: accepts a feature dict, returns explanation dict."""
    explainer = FusionExplainer(
        model=model,
        feature_names=feature_names,
        training_data=training_data,
    )
    instance = np.array([instance_features.get(f, 0.0) for f in feature_names],
                        dtype="float32")
    return explainer.explain(instance, num_features=num_features)
