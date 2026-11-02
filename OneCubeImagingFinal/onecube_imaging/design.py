from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np


def grid_coordinates(count: int, pitch_mm: float) -> list[float]:
    return [float((index - (count - 1) / 2.0) * pitch_mm) for index in range(count)]


def make_voxels(config: dict[str, Any]) -> list[dict[str, Any]]:
    image = config["image"]
    xs = grid_coordinates(int(image["nx"]), float(image["voxel_pitch_mm"]))
    ys = grid_coordinates(int(image["ny"]), float(image["voxel_pitch_mm"]))
    voxels = []
    voxel_id = 0
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            voxels.append({
                "voxel_id": voxel_id,
                "source_id": voxel_id,
                "x_index": ix,
                "y_index": iy,
                "x_mm": x,
                "y_mm": y,
                "z_mm": float(image["plane_z_mm"]),
            })
            voxel_id += 1
    return voxels


def make_poses(config: dict[str, Any]) -> list[dict[str, Any]]:
    acquisition = config["acquisition"]
    xs = grid_coordinates(int(acquisition["pose_nx"]), float(acquisition["pose_pitch_mm"]))
    ys = grid_coordinates(int(acquisition["pose_ny"]), float(acquisition["pose_pitch_mm"]))
    poses = []
    pose_id = 0
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            poses.append({
                "pose_id": pose_id,
                "row_id": pose_id,
                "pose_x_index": ix,
                "pose_y_index": iy,
                "detector_id": int(config["baseline"]["detector_id"]),
                "detector_x_mm": x,
                "detector_y_mm": y,
                "detector_z_mm": float(acquisition["detector_z_mm"]),
                "rotation_x_deg": 0.0,
                "rotation_y_deg": 0.0,
                "rotation_z_deg": 0.0,
                "pose_kind": "physical XY translation; fixed orientation",
            })
            pose_id += 1
    return poses


def d4_representatives(max_offset: int) -> list[tuple[int, int]]:
    return [(dx, dy) for dx in range(max_offset + 1) for dy in range(dx + 1)]


def canonical_offset(dx_index: int, dy_index: int) -> tuple[int, int]:
    values = sorted((abs(int(dx_index)), abs(int(dy_index))), reverse=True)
    return values[0], values[1]


def make_phantom(config: dict[str, Any], voxels: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    phantom = config["phantom"]
    xs = np.asarray(sorted({float(row["x_mm"]) for row in voxels}))
    ys = np.asarray(sorted({float(row["y_mm"]) for row in voxels}))
    activity_shape = np.full((len(ys), len(xs)), float(phantom["background_fraction_of_reference"]))
    centers = np.asarray(phantom["hotspot_centers_mm"], dtype=float)
    weights = np.asarray(phantom["hotspot_relative_weights"], dtype=float)
    sigma = float(phantom["hotspot_sigma_mm"])
    for row in voxels:
        for (cx, cy), weight in zip(centers, weights, strict=True):
            radius2 = (float(row["x_mm"]) - cx) ** 2 + (float(row["y_mm"]) - cy) ** 2
            activity_shape[int(row["y_index"]), int(row["x_index"])] += float(weight) * math.exp(-radius2 / (2.0 * sigma * sigma))
    flattened = activity_shape.ravel(order="C")
    flattened *= float(phantom["total_activity_Bq"]) / float(flattened.sum())
    hot_mask = (activity_shape > float(np.min(activity_shape)) * 1.5).ravel(order="C")
    metadata = {
        "pattern": phantom["pattern"],
        "shape_yx": list(activity_shape.shape),
        "flatten_order": "C/row-major y then x; matches voxel_id",
        "total_activity_Bq": float(flattened.sum()),
        "minimum_voxel_activity_Bq": float(flattened.min()),
        "maximum_voxel_activity_Bq": float(flattened.max()),
        "hot_voxel_count": int(hot_mask.sum()),
        "background_voxel_count": int((~hot_mask).sum()),
        "activity_model": phantom["source_model"],
    }
    return activity_shape, flattened, {**metadata, "hot_mask": hot_mask.astype(int).tolist()}
