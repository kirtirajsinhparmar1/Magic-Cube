"""Forward projection and deterministic Poisson sampling."""

from __future__ import annotations

import numpy as np


def forward_project(projection_operator_counts_per_bq: np.ndarray, x_true_bq: np.ndarray) -> np.ndarray:
    """Compute y_expected=A@x, where A maps Bq per voxel to counts per measurement."""
    matrix = np.asarray(projection_operator_counts_per_bq, dtype=float)
    image = np.asarray(x_true_bq, dtype=float).reshape(-1)
    if matrix.ndim != 2 or matrix.shape[1] != image.size:
        raise ValueError("Projection operator columns must match flattened phantom voxels")
    if not np.isfinite(matrix).all() or not np.isfinite(image).all() or (matrix < 0).any() or (image < 0).any():
        raise ValueError("Projection inputs must be finite and nonnegative")
    return matrix @ image


def poisson_measurements(expected_counts: np.ndarray, seed: int) -> np.ndarray:
    expected = np.asarray(expected_counts, dtype=float)
    if not np.isfinite(expected).all() or (expected < 0).any():
        raise ValueError("Expected Poisson counts must be finite and nonnegative")
    return np.random.default_rng(int(seed)).poisson(expected).astype(float)
