"""Response-region extraction and interpolated spatial FWHM."""

from __future__ import annotations

import numpy as np


def extract_response_regions(
    matrix: np.ndarray,
    voxel_coords_mm: np.ndarray,
    detector_coords_mm: np.ndarray,
    relative_threshold: float = 0.01,
    plane_axes: tuple[int, int] = (0, 2),
) -> dict[str, np.ndarray]:
    """Threshold each measured spatial response and infer its direction from coordinates."""
    response = np.asarray(matrix, dtype=float)
    coords = np.asarray(voxel_coords_mm, dtype=float)
    detectors = np.asarray(detector_coords_mm, dtype=float)
    if not 0 <= relative_threshold <= 1:
        raise ValueError("relative_threshold must be in [0,1]")
    if response.ndim != 2 or coords.shape != (response.shape[1], 3) or detectors.shape != (response.shape[0], 3):
        raise ValueError("Response, voxel coordinates, and detector coordinates are inconsistent")
    masks = np.zeros(response.shape, dtype=bool)
    peaks = np.zeros(response.shape[0], dtype=float)
    angles = np.full(response.shape[0], np.nan, dtype=float)
    centroids = np.full((response.shape[0], 3), np.nan, dtype=float)
    for i, row in enumerate(response):
        peak = float(row.max(initial=0.0))
        peaks[i] = peak
        if peak <= 0:
            continue
        mask = row >= relative_threshold * peak
        masks[i] = mask
        weights = row[mask]
        centroid = np.average(coords[mask], axis=0, weights=weights)
        centroids[i] = centroid
        a0, a1 = plane_axes
        delta = centroid[[a0, a1]] - detectors[i, [a0, a1]]
        if np.linalg.norm(delta) > 0:
            angles[i] = np.degrees(np.arctan2(delta[1], delta[0])) % 360.0
    return {"mask": masks, "peak": peaks, "centroid_mm": centroids, "angle_deg": angles}


def _crossing(x0: float, y0: float, x1: float, y1: float, half: float) -> float:
    if y1 == y0:
        return float((x0 + x1) / 2.0)
    return float(x0 + (half - y0) * (x1 - x0) / (y1 - y0))


def fwhm_profile(axis_mm: np.ndarray, response: np.ndarray, minimum_samples: int = 3) -> dict[str, object]:
    """Measure width between interpolated half-height crossings; flag incomplete profiles."""
    x = np.asarray(axis_mm, dtype=float)
    y = np.asarray(response, dtype=float)
    if x.ndim != 1 or y.shape != x.shape:
        raise ValueError("Profile coordinate and response vectors must have equal one-dimensional shape")
    valid = np.isfinite(x) & np.isfinite(y) & (y >= 0)
    x, y = x[valid], y[valid]
    if x.size:
        order = np.argsort(x)
        x, y = x[order], y[order]
    result: dict[str, object] = {
        "valid": False, "fwhm_mm": None, "peak": float(y.max()) if y.size else None,
        "half_maximum": None, "left_crossing_mm": None, "right_crossing_mm": None,
        "reason": None, "axis_mm": x.tolist(), "profile": y.tolist(),
    }
    if x.size < minimum_samples:
        result["reason"] = f"requires at least {minimum_samples} spatial samples; found {x.size}"
        return result
    peak_index = int(np.argmax(y))
    peak = float(y[peak_index])
    if peak <= 0:
        result["reason"] = "profile peak is zero"
        return result
    half = peak / 2.0
    left = next((k for k in range(peak_index - 1, -1, -1) if y[k] < half <= y[k + 1]), None)
    right = next((k for k in range(peak_index, x.size - 1) if y[k] >= half > y[k + 1]), None)
    if left is None or right is None:
        result["reason"] = "profile does not cross half maximum on both sides"
        result["half_maximum"] = half
        return result
    left_x = _crossing(float(x[left]), float(y[left]), float(x[left + 1]), float(y[left + 1]), half)
    right_x = _crossing(float(x[right]), float(y[right]), float(x[right + 1]), float(y[right + 1]), half)
    result.update({
        "valid": True, "fwhm_mm": float(right_x - left_x), "peak": peak,
        "half_maximum": half, "left_crossing_mm": left_x, "right_crossing_mm": right_x,
    })
    return result


def calculate_response_fwhm(
    matrix: np.ndarray, voxel_coords_mm: np.ndarray, axis: int = 0, minimum_samples: int = 3
) -> list[dict[str, object]]:
    """Form a marginal line profile per measurement by summing over other coordinates."""
    response = np.asarray(matrix, dtype=float)
    coords = np.asarray(voxel_coords_mm, dtype=float)
    results = []
    for measurement_index, row in enumerate(response):
        unique_axis = np.unique(coords[:, axis])
        profile = np.asarray([row[coords[:, axis] == value].sum() for value in unique_axis], dtype=float)
        value = fwhm_profile(unique_axis, profile, minimum_samples=minimum_samples)
        value.update({"measurement_index": measurement_index, "profile_axis": "xyz"[axis]})
        results.append(value)
    return results
