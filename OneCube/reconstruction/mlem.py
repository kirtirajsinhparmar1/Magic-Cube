"""Standard MLEM with explicit stabilization and complete iteration history."""

from __future__ import annotations

from typing import Any

import numpy as np


def mlem(
    projection_operator: np.ndarray,
    measurements: np.ndarray,
    iterations: int,
    epsilon: float = 1e-12,
    initial_value_bq: float = 1.0,
    relative_change_stop: float | None = None,
) -> dict[str, Any]:
    """Reconstruct nonnegative voxel activity; A rows are measurement bins."""
    matrix = np.asarray(projection_operator, dtype=float)
    y = np.asarray(measurements, dtype=float).reshape(-1)
    if matrix.ndim != 2 or matrix.shape[0] != y.size:
        raise ValueError("MLEM matrix rows must match measurement vector")
    if iterations < 1 or epsilon <= 0 or initial_value_bq <= 0:
        raise ValueError("MLEM needs positive iterations, epsilon, and initialization")
    if not np.isfinite(matrix).all() or (matrix < 0).any() or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("MLEM inputs must be finite and nonnegative")
    sensitivity = matrix.T @ np.ones(matrix.shape[0], dtype=float)
    estimate = np.full(matrix.shape[1], float(initial_value_bq), dtype=float)
    estimates = [estimate.copy()]
    history: list[dict[str, float | int]] = []
    for iteration in range(1, iterations + 1):
        predicted = matrix @ estimate
        ratio = np.divide(y, predicted, out=np.zeros_like(y), where=predicted > epsilon)
        backprojection = matrix.T @ ratio
        updated = np.divide(
            estimate * backprojection,
            sensitivity,
            out=np.zeros_like(estimate),
            where=sensitivity > epsilon,
        )
        updated = np.maximum(updated, 0.0)
        relative_change = float(np.linalg.norm(updated - estimate) / max(np.linalg.norm(estimate), epsilon))
        history.append({
            "iteration": iteration,
            "relative_change": relative_change,
            "activity_sum_bq": float(updated.sum()),
            "predicted_count_sum": float((matrix @ updated).sum()),
            "unobservable_voxels": int(np.count_nonzero(sensitivity <= epsilon)),
        })
        estimate = updated
        estimates.append(estimate.copy())
        if relative_change_stop is not None and relative_change <= relative_change_stop:
            break
    return {
        "image_bq": estimate,
        "history": history,
        "iteration_estimates_bq": np.asarray(estimates),
        "sensitivity": sensitivity,
        "epsilon": float(epsilon),
        "configured_iterations": int(iterations),
        "completed_iterations": len(history),
        "relative_change_stop": relative_change_stop,
        "stabilization": "ratio is zero when predicted count <= epsilon; zero-sensitivity voxels update to zero",
    }


def gaussian_postfilter(image: np.ndarray, sigma_voxels: float) -> np.ndarray:
    """Optional, separate nonnegative Gaussian smoothing using only NumPy."""
    values = np.asarray(image, dtype=float)
    if sigma_voxels <= 0:
        raise ValueError("sigma_voxels must be positive")
    radius = max(1, int(np.ceil(3.0 * sigma_voxels)))
    positions = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-0.5 * (positions / sigma_voxels) ** 2)
    kernel /= kernel.sum()
    result = values.copy()
    for axis in range(result.ndim):
        padded = np.pad(result, [(radius, radius) if i == axis else (0, 0) for i in range(result.ndim)], mode="edge")
        result = np.apply_along_axis(lambda line: np.convolve(line, kernel, mode="valid"), axis, padded)
    return np.maximum(result, 0.0)
