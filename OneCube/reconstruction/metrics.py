"""Metrics with undefined quantities represented as null instead of fabricated values."""

from __future__ import annotations

import numpy as np


def reconstruction_metrics(truth: np.ndarray, reconstruction: np.ndarray, epsilon: float = 1e-12) -> dict[str, float | None]:
    x = np.asarray(truth, dtype=float).reshape(-1)
    r = np.asarray(reconstruction, dtype=float).reshape(-1)
    if x.shape != r.shape or not np.isfinite(x).all() or not np.isfinite(r).all():
        raise ValueError("Metric inputs must be finite and have the same shape")
    error = r - x
    denominator = max(float(np.linalg.norm(x)), epsilon)
    corr: float | None = None
    if x.size > 1 and np.std(x) > 0 and np.std(r) > 0:
        corr = float(np.corrcoef(x, r)[0, 1])
    recovery = float(r.sum() / x.sum()) if x.sum() > epsilon else None
    return {
        "mse_bq2": float(np.mean(error**2)),
        "rmse_bq": float(np.sqrt(np.mean(error**2))),
        "normalized_error": float(np.linalg.norm(error) / denominator),
        "correlation": corr,
        "activity_recovery_ratio": recovery,
    }
