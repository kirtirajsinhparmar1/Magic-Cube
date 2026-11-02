from __future__ import annotations

from typing import Any

import numpy as np

from onecube_imaging.design import canonical_offset


def assemble_system_response(
    calibration_rows: list[dict[str, str]],
    poses: list[dict[str, Any]],
    voxels: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, np.ndarray]:
    measured = {
        (int(row["offset_dx_index"]), int(row["offset_dy_index"])): row
        for row in calibration_rows
    }
    pitch = float(config["image"]["voxel_pitch_mm"])
    calibration_activity = float(config["acquisition"]["calibration_activity_Bq"])
    calibration_exposure = float(config["acquisition"]["calibration_exposure_s"])
    phantom_exposure = float(config["acquisition"]["phantom_exposure_s"])
    shape = (len(poses), len(voxels))
    raw = np.zeros(shape, dtype=np.float64)
    rate = np.zeros(shape, dtype=np.float64)
    provenance_task = np.full(shape, -1, dtype=np.int64)
    for i, pose in enumerate(poses):
        for j, voxel in enumerate(voxels):
            dx_index = int(round((float(voxel["x_mm"]) - float(pose["detector_x_mm"])) / pitch))
            dy_index = int(round((float(voxel["y_mm"]) - float(pose["detector_y_mm"])) / pitch))
            key = canonical_offset(dx_index, dy_index)
            if key not in measured:
                raise ValueError(f"Relative source-detector offset {key} is outside the calibrated grid")
            calibration = measured[key]
            count = float(calibration["raw_singles_count"])
            actual_activity = float(calibration["activity_Bq"])
            actual_exposure = float(calibration["acquisition_s"])
            if actual_activity <= 0 or actual_exposure <= 0:
                raise ValueError(f"Invalid calibration normalization for offset {key}")
            raw[i, j] = count
            rate[i, j] = count / (actual_activity * actual_exposure)
            provenance_task[i, j] = int(calibration["task_id"])
    count_operator = rate * phantom_exposure
    row_sums = rate.sum(axis=1, keepdims=True)
    ppdf = np.divide(rate, row_sums, out=np.zeros_like(rate), where=row_sums > 0)
    return {
        "raw_counts_symmetry_expanded": raw,
        "rate_response_cps_per_bq": rate,
        "count_operator_counts_per_bq": count_operator,
        "row_normalized_ppdf": ppdf,
        "calibration_task_id_for_element": provenance_task,
        "calibration_count_vector": np.asarray(
            [int(row["raw_singles_count"]) for row in calibration_rows], dtype=np.int64
        ),
    }

