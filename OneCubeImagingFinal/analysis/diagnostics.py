from __future__ import annotations

from typing import Any

import numpy as np


def matrix_diagnostics(matrix: np.ndarray, relative_tolerance: float) -> dict[str, Any]:
    matrix = np.asarray(matrix, dtype=np.float64)
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    maximum = float(singular_values.max(initial=0.0))
    cutoff = maximum * float(relative_tolerance)
    rank = int(np.count_nonzero(singular_values > cutoff)) if maximum > 0 else 0
    positive = singular_values[singular_values > cutoff]
    condition = float(positive.max() / positive.min()) if positive.size else None
    column_norms = np.linalg.norm(matrix, axis=0)
    return {
        "matrix_shape": list(matrix.shape),
        "measurement_count": int(matrix.shape[0]),
        "spatial_voxel_count": int(matrix.shape[1]),
        "numerical_rank": rank,
        "rank_relative_tolerance": float(relative_tolerance),
        "singular_values": singular_values.tolist(),
        "condition_number_on_retained_subspace": condition,
        "zero_sensitivity_voxel_ids": np.flatnonzero(column_norms == 0).astype(int).tolist(),
        "minimum_column_norm": float(column_norms.min()) if column_norms.size else 0.0,
        "maximum_column_norm": float(column_norms.max()) if column_norms.size else 0.0,
        "identifiability_note": "Rank and conditioning are diagnostics, not a guarantee of stable spatial recovery; report the observed singular spectrum with reconstruction metrics.",
    }
