"""Angular sampling coverage (ASCI) from measured response masks and view directions."""

from __future__ import annotations

import numpy as np


def calculate_asci(
    response_masks: np.ndarray, view_angles_deg: np.ndarray, angular_bins: int = 360
) -> dict[str, np.ndarray | dict[str, float | int]]:
    """ASCI_j is the fraction of configured angular bins covering voxel j."""
    masks = np.asarray(response_masks, dtype=bool)
    angles = np.asarray(view_angles_deg, dtype=float)
    if masks.ndim != 2 or angles.shape != (masks.shape[0],) or angular_bins < 1:
        raise ValueError("Expected masks[measurement,voxel], one angle per measurement, and positive bin count")
    occupancy = np.zeros((masks.shape[1], angular_bins), dtype=bool)
    valid_views = 0
    for i, angle in enumerate(angles):
        if not np.isfinite(angle) or not masks[i].any():
            continue
        bin_index = int(np.floor((angle % 360.0) * angular_bins / 360.0)) % angular_bins
        occupancy[:, bin_index] |= masks[i]
        valid_views += 1
    fraction = occupancy.sum(axis=1, dtype=float) / float(angular_bins)
    summary = {
        "angular_bins": int(angular_bins),
        "valid_measurements": int(valid_views),
        "occupied_angular_bins": int(np.count_nonzero(occupancy.any(axis=0))),
        "mean_fraction": float(fraction.mean()) if fraction.size else 0.0,
        "mean_percent": float(fraction.mean() * 100.0) if fraction.size else 0.0,
        "minimum_percent": float(fraction.min() * 100.0) if fraction.size else 0.0,
        "maximum_percent": float(fraction.max() * 100.0) if fraction.size else 0.0,
    }
    return {"occupancy": occupancy, "fraction": fraction, "summary": summary}
