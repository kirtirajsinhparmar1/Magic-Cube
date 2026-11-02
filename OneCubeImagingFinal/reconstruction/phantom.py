from __future__ import annotations

from typing import Any

import numpy as np

from onecube_imaging.design import make_phantom


def prepare_phantom(
    config: dict[str, Any], voxels: list[dict[str, Any]]
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    return make_phantom(config, voxels)


def source_rows(
    phantom_vector: np.ndarray,
    voxels: list[dict[str, Any]],
    activity_total_bq: float,
) -> list[dict[str, Any]]:
    if len(phantom_vector) != len(voxels):
        raise ValueError("Phantom activity vector must match voxel map columns")
    if np.any(phantom_vector < 0) or not np.isfinite(phantom_vector).all():
        raise ValueError("Phantom activities must be finite and nonnegative")
    if not np.isclose(float(phantom_vector.sum()), float(activity_total_bq), rtol=1e-12):
        raise ValueError("Voxel source activities do not sum to the configured phantom activity")
    return [
        {**voxel, "activity_Bq": float(phantom_vector[index])}
        for index, voxel in enumerate(voxels)
    ]
