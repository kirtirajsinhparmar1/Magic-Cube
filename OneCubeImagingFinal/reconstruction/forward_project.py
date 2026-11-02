from __future__ import annotations

import numpy as np


def forward_project(
    count_operator: np.ndarray,
    activity_vector_bq: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    operator = np.asarray(count_operator, dtype=np.float64)
    activity = np.asarray(activity_vector_bq, dtype=np.float64)
    if operator.ndim != 2 or activity.ndim != 1 or operator.shape[1] != activity.size:
        raise ValueError("Forward projection requires H[n_measurements,n_voxels] and x[n_voxels]")
    if not np.isfinite(operator).all() or not np.isfinite(activity).all():
        raise ValueError("Forward-projection inputs must be finite")
    if np.any(operator < 0) or np.any(activity < 0):
        raise ValueError("Forward-projection inputs must be nonnegative")
    expected = operator @ activity
    if not np.isfinite(expected).all():
        raise FloatingPointError("Expected projection contains non-finite values")
    noisy = np.random.default_rng(int(seed)).poisson(expected).astype(np.float64)
    return expected, noisy


def measured_projection(counts: np.ndarray, measurement_count: int) -> np.ndarray:
    values = np.asarray(counts, dtype=np.float64)
    if values.shape != (measurement_count,) or np.any(values < 0) or not np.isfinite(values).all():
        raise ValueError("Measured counts must be a finite nonnegative vector in measurement-row order")
    return values
