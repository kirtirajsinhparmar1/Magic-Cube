from __future__ import annotations

from typing import Any

import numpy as np


def compute_sensitivity(
    rate_response: np.ndarray,
    count_operator: np.ndarray,
    poses: list[dict[str, Any]],
    voxels: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    rate_response = np.asarray(rate_response, dtype=np.float64)
    count_operator = np.asarray(count_operator, dtype=np.float64)
    if (rate_response.ndim != 2 or rate_response.shape != count_operator.shape
            or rate_response.shape != (len(poses), len(voxels))):
        raise ValueError("Rate and count-operator matrices must match the measurement and voxel maps")
    if (not np.isfinite(rate_response).all() or not np.isfinite(count_operator).all()
            or np.any(rate_response < 0) or np.any(count_operator < 0)):
        raise ValueError("Sensitivity inputs must be finite and nonnegative")
    pose_exposure = np.asarray(
        [float(pose["exposure_s"]) for pose in poses], dtype=np.float64
    )
    if not np.isfinite(pose_exposure).all() or np.any(pose_exposure <= 0):
        raise ValueError("Every physical measurement pose must have a positive finite exposure")
    # The requested system sensitivity is the sum of calibrated pose rates.
    sensitivity = rate_response.sum(axis=0)
    # Also report the sequential-protocol average and integrated counts/Bq.
    total_scan_counts_per_bq = count_operator.sum(axis=0)
    scan_average_cps_per_bq = total_scan_counts_per_bq / float(pose_exposure.sum())
    ny = max(int(row["y_index"]) for row in voxels) + 1
    nx = max(int(row["x_index"]) for row in voxels) + 1
    image = np.zeros((ny, nx), dtype=np.float64)
    for voxel, value in zip(voxels, sensitivity, strict=True):
        image[int(voxel["y_index"]), int(voxel["x_index"])] = value
    center = next(
        (index for index, voxel in enumerate(voxels)
         if int(voxel["x_index"]) == nx // 2 and int(voxel["y_index"]) == ny // 2),
        None,
    )
    values = sensitivity
    scan_average_center = float(scan_average_cps_per_bq[center]) if center is not None else None
    summary = {
        "definition": "S_j = sum_i R_ij over the configured physical detector-pose measurements",
        "units": "cps/Bq",
        "scan_average_definition": "sum_i(T_i*R_ij) / sum_i(T_i) for the sequential scan protocol",
        "central_voxel_index": center,
        "central_cps_per_bq": float(values[center]) if center is not None else None,
        "mean_cps_per_bq": float(values.mean()),
        "minimum_cps_per_bq": float(values.min()),
        "maximum_cps_per_bq": float(values.max()),
        "mean_cps_per_mbq": float(values.mean() * 1.0e6),
        "central_cps_per_mbq": float(values[center] * 1.0e6) if center is not None else None,
        "minimum_cps_per_mbq": float(values.min() * 1.0e6),
        "maximum_cps_per_mbq": float(values.max() * 1.0e6),
        "scan_average_central_cps_per_bq": scan_average_center,
        "scan_average_mean_cps_per_bq": float(scan_average_cps_per_bq.mean()),
        "scan_average_mean_cps_per_mbq": float(scan_average_cps_per_bq.mean() * 1.0e6),
        "total_scan_counts_per_bq_mean": float(total_scan_counts_per_bq.mean()),
        "sum_of_pose_rate_cps_per_bq_mean": float(sensitivity.mean()),
        "pose_exposure_s": float(pose_exposure.sum()),
        "voxel_count": len(voxels),
    }
    return sensitivity, image, summary

