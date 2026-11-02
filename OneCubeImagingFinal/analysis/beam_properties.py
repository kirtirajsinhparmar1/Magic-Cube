from __future__ import annotations

from typing import Any

import numpy as np


def _crossing(x0: float, y0: float, x1: float, y1: float, level: float) -> float:
    if y1 == y0:
        return float((x0 + x1) / 2.0)
    return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0))


def fwhm_profile(x: np.ndarray, values: np.ndarray, fraction: float = 0.5) -> dict[str, Any]:
    x = np.asarray(x, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    if x.ndim != 1 or values.ndim != 1 or len(x) != len(values) or len(x) < 3:
        return {"valid": False, "reason": "profile needs at least three paired samples"}
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(values)):
        return {"valid": False, "reason": "profile contains non-finite values"}
    if not np.all(np.diff(x) > 0):
        return {"valid": False, "reason": "profile coordinates must be strictly increasing"}
    peak_index = int(np.argmax(values))
    peak = float(values[peak_index])
    if peak <= 0:
        return {"valid": False, "reason": "profile has no positive peak", "peak": peak}
    half = peak * fraction
    left_index = next((k for k in range(peak_index - 1, -1, -1) if values[k] < half), None)
    right_index = next((k for k in range(peak_index + 1, len(values)) if values[k] < half), None)
    base = {
        "peak_index": peak_index,
        "peak_x_mm": float(x[peak_index]),
        "peak": peak,
        "half_maximum": half,
        "fraction": float(fraction),
    }
    if left_index is None or right_index is None:
        missing = "left" if left_index is None else "right" if right_index is None else "both"
        return {**base, "valid": False, "reason": f"no {missing} half-maximum crossing inside sampled FOV"}
    left = _crossing(x[left_index], values[left_index], x[left_index + 1], values[left_index + 1], half)
    right = _crossing(x[right_index - 1], values[right_index - 1], x[right_index], values[right_index], half)
    if right <= left:
        return {**base, "valid": False, "reason": "interpolated crossings are not ordered"}
    return {
        **base,
        "valid": True,
        "left_crossing_mm": left,
        "right_crossing_mm": right,
        "fwhm_mm": float(right - left),
    }


def characterize_profiles(
    rate_response: np.ndarray,
    voxels: list[dict[str, Any]],
    poses: list[dict[str, Any]],
    threshold_fraction: float,
    half_max_fraction: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    ny = max(int(v["y_index"]) for v in voxels) + 1
    nx = max(int(v["x_index"]) for v in voxels) + 1
    xs = np.asarray([float(v) for v in sorted({row["x_mm"] for row in voxels})])
    ys = np.asarray([float(v) for v in sorted({row["y_mm"] for row in voxels})])
    masks = np.zeros_like(rate_response, dtype=bool)
    measurements = []
    for row_id, row in enumerate(rate_response):
        if not np.isfinite(row).all() or float(row.max(initial=0.0)) <= 0:
            measurements.append({
                "row_id": row_id, "valid": False, "reason": "response row has no positive finite peak"
            })
            continue
        peak_index = int(np.argmax(row))
        peak_voxel = voxels[peak_index]
        masks[row_id] = row >= float(row.max()) * threshold_fraction
        ix, iy = int(peak_voxel["x_index"]), int(peak_voxel["y_index"])
        profile_x = row.reshape(ny, nx)[iy, :]
        profile_y = row.reshape(ny, nx)[:, ix]
        x_result = fwhm_profile(xs, profile_x, half_max_fraction)
        y_result = fwhm_profile(ys, profile_y, half_max_fraction)
        measurements.append({
            "row_id": row_id,
            "pose_id": int(poses[row_id]["pose_id"]),
            "detector_pose_mm": [
                float(poses[row_id]["detector_x_mm"]),
                float(poses[row_id]["detector_y_mm"]),
                float(poses[row_id]["detector_z_mm"]),
            ],
            "peak_voxel_id": int(peak_voxel["voxel_id"]),
            "peak_source_mm": [float(peak_voxel["x_mm"]), float(peak_voxel["y_mm"])],
            "peak_response_cps_per_bq": float(row[peak_index]),
            "response_mask_voxel_count": int(masks[row_id].sum()),
            "x_profile": {"coordinates_mm": xs.tolist(), "values": profile_x.tolist(), **x_result},
            "y_profile": {"coordinates_mm": ys.tolist(), "values": profile_y.tolist(), **y_result},
            "valid": bool(x_result.get("valid") or y_result.get("valid")),
            "fwhm_x_mm": x_result.get("fwhm_mm"),
            "fwhm_y_mm": y_result.get("fwhm_mm"),
            "reason": None if (x_result.get("valid") or y_result.get("valid"))
            else f"x: {x_result.get('reason')}; y: {y_result.get('reason')}",
        })
    all_widths = [
        float(value)
        for item in measurements
        for value in (item.get("fwhm_x_mm"), item.get("fwhm_y_mm"))
        if value is not None
    ]
    result = {
        "threshold_fraction_of_row_peak": float(threshold_fraction),
        "half_maximum_fraction": float(half_max_fraction),
        "profile_method": "axis-aligned source-grid profiles through each row's response maximum; linear interpolation at half maximum",
        "measurement_count": len(measurements),
        "valid_profile_count": sum(
            int(item.get("x_profile", {}).get("valid", False))
            + int(item.get("y_profile", {}).get("valid", False))
            for item in measurements
        ),
        "mean_fwhm_mm": float(np.mean(all_widths)) if all_widths else None,
        "measurements": measurements,
    }
    return masks, result

