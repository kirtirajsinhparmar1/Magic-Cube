#!/usr/bin/env python3
"""Assemble the measured OneCube response operator and run system characterization."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.asci import evaluate_asci
from analysis.beam_properties import characterize_profiles
from analysis.diagnostics import matrix_diagnostics
from analysis.ji import calculate_ji
from analysis.response import assemble_system_response
from analysis.sensitivity import compute_sensitivity
from onecube_imaging.io import load_config, read_csv, save_npy, write_csv, write_runtime_json
from visualization.imaging_plots import plot_system_characterization


def assemble_and_analyze() -> dict:
    config = load_config(PROJECT_ROOT)
    voxels = read_csv(PROJECT_ROOT / "runtime/manifests/image_voxel_map.csv")
    poses = read_csv(PROJECT_ROOT / "runtime/manifests/measurement_row_map.csv")
    counts = read_csv(PROJECT_ROOT / "runtime/reduced/calibration_counts.csv")
    for rows in (voxels, poses, counts):
        for row in rows:
            for key in tuple(row):
                if row[key] == "":
                    continue
                if key in {
                    "task_id", "offset_dx_index", "offset_dy_index", "detector_id",
                    "pose_id", "row_id", "pose_x_index", "pose_y_index",
                    "x_index", "y_index", "source_id", "seed", "raw_singles_count",
                    "raw_hits_count",
                }:
                    row[key] = int(row[key])
                elif key.endswith("_mm") or key.endswith("_Bq") or key.endswith("_s") or key == "source_energy_keV":
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        pass
    matrices = assemble_system_response(counts, poses, voxels, config)
    rate = matrices["rate_response_cps_per_bq"]
    count_operator = matrices["count_operator_counts_per_bq"]
    ppdf = matrices["row_normalized_ppdf"]
    raw = matrices["raw_counts_symmetry_expanded"]
    masks, fwhm = characterize_profiles(
        rate,
        voxels,
        poses,
        float(config["analysis"]["response_mask_fraction_of_row_peak"]),
        float(config["analysis"]["fwhm_half_max_fraction"]),
    )
    sensitivity_vector, sensitivity_map, sensitivity_summary = compute_sensitivity(
        rate, count_operator, poses, voxels
    )
    asci = evaluate_asci(config, poses)
    ji = calculate_ji(sensitivity_summary, fwhm, asci)
    diagnostics = matrix_diagnostics(
        count_operator, float(config["analysis"]["svd_relative_tolerance"])
    )
    outputs = PROJECT_ROOT / "results"
    save_npy(outputs / "system_matrix/raw_counts_symmetry_expanded.npy", raw)
    save_npy(outputs / "system_matrix/rate_response_cps_per_bq.npy", rate)
    save_npy(outputs / "system_matrix/count_operator_counts_per_bq.npy", count_operator)
    save_npy(outputs / "system_matrix/row_normalized_ppdf.npy", ppdf)
    save_npy(outputs / "system_matrix/calibration_task_id_for_element.npy", matrices["calibration_task_id_for_element"])
    save_npy(outputs / "system_matrix/response_masks.npy", masks.astype(np.uint8))
    save_npy(outputs / "sensitivity/sensitivity_cps_per_bq.npy", sensitivity_vector)
    save_npy(outputs / "sensitivity/sensitivity_map_cps_per_bq.npy", sensitivity_map)
    save_npy(outputs / "sensitivity/sensitivity_map_cps_per_mbq.npy", sensitivity_map * 1.0e6)
    write_csv(
        outputs / "system_matrix/rate_response_cps_per_bq.csv",
        [
            {"row_id": i, "voxel_id": j, "rate_response_cps_per_bq": float(rate[i, j]),
             "raw_calibration_count_symmetry_expanded": int(raw[i, j]),
             "calibration_task_id": int(matrices["calibration_task_id_for_element"][i, j])}
            for i in range(rate.shape[0]) for j in range(rate.shape[1])
        ],
        ["row_id", "voxel_id", "rate_response_cps_per_bq",
         "raw_calibration_count_symmetry_expanded", "calibration_task_id"],
    )
    write_csv(
        outputs / "system_matrix/count_operator_counts_per_bq.csv",
        [
            {"row_id": i, "voxel_id": j, "expected_counts_per_bq": float(count_operator[i, j])}
            for i in range(count_operator.shape[0]) for j in range(count_operator.shape[1])
        ],
        ["row_id", "voxel_id", "expected_counts_per_bq"],
    )
    write_csv(
        outputs / "sensitivity/sensitivity_voxel_map.csv",
        [
            {"voxel_id": index, "x_mm": float(voxel["x_mm"]), "y_mm": float(voxel["y_mm"]),
             "sensitivity_cps_per_bq": float(sensitivity_vector[index]),
             "sensitivity_cps_per_mbq": float(sensitivity_vector[index] * 1.0e6)}
            for index, voxel in enumerate(voxels)
        ],
        ["voxel_id", "x_mm", "y_mm", "sensitivity_cps_per_bq", "sensitivity_cps_per_mbq"],
    )
    write_csv(
        outputs / "fwhm/response_profile_summary.csv",
        [
            {"row_id": row["row_id"], "pose_id": row.get("pose_id"),
             "peak_voxel_id": row.get("peak_voxel_id"),
             "peak_response_cps_per_bq": row.get("peak_response_cps_per_bq"),
             "response_mask_voxel_count": row.get("response_mask_voxel_count"),
             "fwhm_x_mm": row.get("fwhm_x_mm"), "fwhm_y_mm": row.get("fwhm_y_mm"),
             "valid": row.get("valid"), "reason": row.get("reason")}
            for row in fwhm["measurements"]
        ],
        ["row_id", "pose_id", "peak_voxel_id", "peak_response_cps_per_bq",
         "response_mask_voxel_count", "fwhm_x_mm", "fwhm_y_mm", "valid", "reason"],
    )
    write_runtime_json(outputs / "sensitivity/sensitivity_summary.json", sensitivity_summary)
    write_runtime_json(outputs / "fwhm/fwhm_summary.json", fwhm)
    write_runtime_json(outputs / "asci/asci_applicability.json", asci)
    write_runtime_json(outputs / "asci/ji_result.json", ji)
    write_runtime_json(outputs / "system_matrix/information_diagnostics.json", diagnostics)
    write_runtime_json(outputs / "response/response_summary.json", {
        "matrix_orientation": "R[i,j]: i=independent detector-pose measurement row; j=row-major source/image voxel",
        "absolute_response_units": "cps/Bq",
        "count_operator_units": "expected counts/Bq for configured phantom exposure",
        "matrix_shape": list(rate.shape),
        "raw_count_note": "raw calibration counts from 28 GATE conditions are expanded only by documented D4 symmetry; matrix provenance gives the measured task id for each element",
        "row_normalized_ppdf": "each nonzero response row divided by its own sum; retained for visualization, never used for MLEM",
        "nonzero_response_fraction": float(np.count_nonzero(rate) / rate.size),
        "zero_response_elements": int(np.count_nonzero(rate == 0)),
    })
    plots = plot_system_characterization(
        PROJECT_ROOT, voxels, poses, rate, ppdf, sensitivity_map,
        sensitivity_map / max(float(sensitivity_map.max()), np.finfo(float).eps),
        masks, fwhm, np.asarray(diagnostics["singular_values"]),
    )
    result = {
        "matrix_shape": list(rate.shape),
        "measurement_rows": len(poses),
        "image_voxels": len(voxels),
        "unique_calibration_conditions": len(counts),
        "sensitivity_summary": sensitivity_summary,
        "fwhm_valid_axes": fwhm["valid_profile_count"],
        "fwhm_measurement_rows": fwhm["measurement_count"],
        "asci_status": asci["status"],
        "ji_defined": ji["valid"],
        "matrix_diagnostics": diagnostics,
        "generated_plots": plots,
    }
    write_runtime_json(PROJECT_ROOT / "runtime/provenance/system_analysis.json", result)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    try:
        assemble_and_analyze()
    except Exception as error:
        print(f"System response analysis failed: {error}", file=sys.stderr)
        raise SystemExit(1)
