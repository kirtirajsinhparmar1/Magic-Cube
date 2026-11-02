from __future__ import annotations

import math
from typing import Any

import numpy as np


def _poisson_log_likelihood(y: np.ndarray, predicted: np.ndarray, epsilon: float) -> float:
    safe = np.maximum(predicted, epsilon)
    terms = y * np.log(safe) - safe
    constants = np.fromiter((math.lgamma(float(value) + 1.0) for value in y), dtype=np.float64, count=y.size)
    return float(np.sum(terms - constants))


def mlem(
    operator: np.ndarray,
    measurements: np.ndarray,
    iterations: int,
    epsilon: float,
    initial_activity_bq: np.ndarray | None = None,
    relative_change_stop: float | None = None,
    stop_patience: int = 3,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Standard nonnegative MLEM for H[measurement, voxel] and activity x in Bq."""
    h = np.asarray(operator, dtype=np.float64)
    y = np.asarray(measurements, dtype=np.float64)
    if h.ndim != 2 or y.ndim != 1 or h.shape[0] != y.size:
        raise ValueError("MLEM contract is H[n_measurements,n_voxels], y[n_measurements]")
    if iterations <= 0 or epsilon <= 0 or stop_patience <= 0:
        raise ValueError("MLEM iterations, epsilon, and patience must be positive")
    if not np.isfinite(h).all() or not np.isfinite(y).all() or np.any(h < 0) or np.any(y < 0):
        raise ValueError("MLEM inputs must be finite and nonnegative")
    sensitivity = h.T @ np.ones(h.shape[0], dtype=np.float64)
    observable = sensitivity > 0
    if initial_activity_bq is None:
        total = max(float(y.sum()), epsilon)
        x = np.full(h.shape[1], total / max(int(observable.sum()), 1), dtype=np.float64)
    else:
        x = np.asarray(initial_activity_bq, dtype=np.float64).copy()
        if x.shape != (h.shape[1],) or not np.isfinite(x).all() or np.any(x < 0):
            raise ValueError("MLEM initialization must be a finite nonnegative vector matching image voxels")
    x[~observable] = 0.0
    x[observable] = np.maximum(x[observable], epsilon)
    estimates = [x.copy()]
    initial_prediction = h @ x
    likelihood = [_poisson_log_likelihood(y, initial_prediction, epsilon)]
    relative_changes = [None]
    stopped_early = False
    below_tolerance = 0
    completed = 0
    for iteration in range(1, int(iterations) + 1):
        predicted = h @ x
        ratio = np.divide(y, np.maximum(predicted, epsilon), out=np.zeros_like(y), where=y > 0)
        backprojection = h.T @ ratio
        update_factor = np.divide(
            backprojection,
            np.maximum(sensitivity, epsilon),
            out=np.zeros_like(backprojection),
            where=observable,
        )
        updated = x * update_factor
        updated[~observable] = 0.0
        updated = np.maximum(updated, 0.0)
        delta = float(np.linalg.norm(updated - x) / max(np.linalg.norm(x), epsilon))
        x = updated
        estimates.append(x.copy())
        likelihood.append(_poisson_log_likelihood(y, h @ x, epsilon))
        relative_changes.append(delta)
        completed = iteration
        if relative_change_stop is not None and delta <= relative_change_stop:
            below_tolerance += 1
            if below_tolerance >= stop_patience:
                stopped_early = True
                break
        else:
            below_tolerance = 0
    history = {
        "configured_iterations": int(iterations),
        "completed_iterations": completed,
        "epsilon": float(epsilon),
        "initialization": "positive uniform over observable voxels; initial vector stored",
        "sensitivity_vector": sensitivity.tolist(),
        "observable_voxel_mask": observable.astype(int).tolist(),
        "zero_sensitivity_policy": "unobservable voxels are fixed to zero and excluded from normalization",
        "relative_change_stop": relative_change_stop,
        "stop_patience": int(stop_patience),
        "stopped_early": stopped_early,
        "relative_change": relative_changes,
        "poisson_log_likelihood": likelihood,
        "estimate_history_bq": np.asarray(estimates).tolist(),
        "filtering": "none",
    }
    return x, history
