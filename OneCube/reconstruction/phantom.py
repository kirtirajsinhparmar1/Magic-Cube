"""Synthetic phantom generation on the system-matrix voxel ordering."""

from __future__ import annotations

from typing import Any

import numpy as np


def make_phantom(
    voxel_coords_mm: np.ndarray,
    voxel_ids: list[int | str],
    image_shape: tuple[int, ...],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build uniform, single-voxel, or Gaussian activity on existing matrix columns."""
    coords = np.asarray(voxel_coords_mm, dtype=float)
    if int(np.prod(image_shape)) != len(voxel_ids) or coords.shape != (len(voxel_ids), 3):
        raise ValueError("Phantom image shape and voxel map must match system-matrix columns")
    kind = str(config.get("pattern", "uniform")).lower()
    activity_bq = float(config["total_activity_bq"])
    if activity_bq < 0 or not np.isfinite(activity_bq):
        raise ValueError("Phantom activity must be finite and nonnegative")
    weights = np.zeros(len(voxel_ids), dtype=float)
    if kind == "uniform":
        weights.fill(1.0)
    elif kind == "single_voxel":
        target_id = config.get("voxel_id")
        index = voxel_ids.index(target_id) if target_id in voxel_ids else int(np.argmin(np.linalg.norm(coords, axis=1)))
        weights[index] = 1.0
    elif kind == "gaussian":
        center = np.asarray(config.get("center_mm", [0.0, 0.0, 0.0]), dtype=float)
        sigma = np.asarray(config.get("sigma_mm", [1.0, 1.0, 1.0]), dtype=float)
        if center.shape != (3,) or sigma.shape != (3,) or np.any(sigma <= 0):
            raise ValueError("Gaussian phantom needs three center and positive sigma values")
        weights = np.exp(-0.5 * np.sum(((coords - center) / sigma) ** 2, axis=1))
    else:
        raise ValueError(f"Unsupported phantom pattern: {kind}")
    if weights.sum() <= 0:
        raise ValueError("Phantom pattern has no support on the configured voxel grid")
    x_true = activity_bq * weights / weights.sum()
    image = x_true.reshape(image_shape)
    return {
        "image": image,
        "x_true": x_true,
        "metadata": {
            "pattern": kind,
            "total_activity_bq": activity_bq,
            "image_shape": list(image_shape),
            "voxel_ordering": "system_matrix_metadata.source_ids; last axis varies fastest",
            "voxel_ids": list(voxel_ids),
            "voxel_coords_mm": coords.tolist(),
            "activity_units": "Bq per voxel",
            "synthetic": True,
        },
    }
