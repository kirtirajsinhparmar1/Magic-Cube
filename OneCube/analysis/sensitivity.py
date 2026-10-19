"""Sensitivity from a measurement-by-voxel system response."""

from __future__ import annotations

import numpy as np


def calculate_sensitivity(matrix: np.ndarray, voxel_coords_mm: np.ndarray) -> tuple[np.ndarray, dict[str, float | int]]:
    """Return S_j=sum_i A[i,j] and spatial summary; input units are preserved."""
    response = np.asarray(matrix, dtype=float)
    coords = np.asarray(voxel_coords_mm, dtype=float)
    if response.ndim != 2 or coords.shape != (response.shape[1], 3):
        raise ValueError("Expected A[measurement,voxel] and one xyz coordinate per voxel")
    vector = response.sum(axis=0)
    center = np.mean(coords, axis=0)
    central_index = int(np.argmin(np.linalg.norm(coords - center, axis=1)))
    return vector, {
        "central_voxel_index": central_index,
        "central": float(vector[central_index]),
        "mean": float(vector.mean()),
        "minimum": float(vector.min()),
        "maximum": float(vector.max()),
        "voxel_count": int(vector.size),
    }
