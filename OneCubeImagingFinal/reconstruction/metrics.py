from __future__ import annotations

from typing import Any

import numpy as np


def reconstruction_metrics(
    truth: np.ndarray,
    estimate: np.ndarray,
    hot_mask: np.ndarray,
    background_mask: np.ndarray,
    measurements: np.ndarray | None = None,
    predicted_measurements: np.ndarray | None = None,
) -> dict[str, Any]:
    truth = np.asarray(truth, dtype=np.float64)
    estimate = np.asarray(estimate, dtype=np.float64)
    if truth.shape != estimate.shape or truth.ndim != 1:
        raise ValueError("Truth and reconstruction must be same-length flattened voxel vectors")
    error = estimate - truth
    mse = float(np.mean(error ** 2))
    correlation = None
    if truth.size > 1 and np.std(truth) > 0 and np.std(estimate) > 0:
        correlation = float(np.corrcoef(truth, estimate)[0, 1])
    hot = np.asarray(hot_mask, dtype=bool)
    background = np.asarray(background_mask, dtype=bool)
    true_contrast = rec_contrast = contrast_recovery = None
    if hot.shape == truth.shape and background.shape == truth.shape and hot.any() and background.any():
        true_bg = float(truth[background].mean())
        rec_bg = float(estimate[background].mean())
        if true_bg > 0 and rec_bg > 0:
            true_contrast = float((truth[hot].mean() - true_bg) / true_bg)
            rec_contrast = float((estimate[hot].mean() - rec_bg) / rec_bg)
            if true_contrast != 0:
                contrast_recovery = float(rec_contrast / true_contrast)
        background_rmse = float(np.sqrt(np.mean((estimate[background] - truth[background]) ** 2)))
    else:
        background_rmse = None
    result: dict[str, Any] = {
        "mse_bq2": mse,
        "rmse_bq": float(np.sqrt(mse)),
        "normalized_error": float(np.linalg.norm(error) / max(np.linalg.norm(truth), np.finfo(float).eps)),
        "correlation": correlation,
        "activity_recovery_ratio": float(estimate.sum() / max(truth.sum(), np.finfo(float).eps)),
        "true_total_activity_bq": float(truth.sum()),
        "reconstructed_total_activity_bq": float(estimate.sum()),
        "hot_region_contrast_recovery": contrast_recovery,
        "true_hot_to_background_contrast": true_contrast,
        "reconstructed_hot_to_background_contrast": rec_contrast,
        "background_rmse_bq": background_rmse,
    }
    if measurements is not None and predicted_measurements is not None:
        measured = np.asarray(measurements, dtype=np.float64)
        predicted = np.asarray(predicted_measurements, dtype=np.float64)
        residual = measured - predicted
        result["projection_fit"] = {
            "measurement_count": int(measured.size),
            "residual_l2": float(np.linalg.norm(residual)),
            "residual_rmse_counts": float(np.sqrt(np.mean(residual ** 2))),
            "poisson_deviance": float(2.0 * np.sum(
                np.where(measured > 0, measured * np.log(measured / np.maximum(predicted, 1e-12)), 0.0)
                - (measured - predicted)
            )),
        }
    return result
