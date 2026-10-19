#!/usr/bin/env python3
"""Run OneCube downstream imaging analysis using existing validated artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.asci import calculate_asci
from analysis.beam_properties import calculate_response_fwhm, extract_response_regions
from analysis.ji import calculate_ji
from analysis.response import load_system_response
from analysis.sensitivity import calculate_sensitivity
from reconstruction.forward_project import forward_project, poisson_measurements
from reconstruction.metrics import reconstruction_metrics
from reconstruction.mlem import gaussian_postfilter, mlem
from reconstruction.phantom import make_phantom
from visualization.imaging_plots import generate_imaging_plots


def _json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _write_sensitivity_csv(path: Path, ids: list[int | str], coords: np.ndarray, sens: np.ndarray,
                           raw_counts: np.ndarray) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_id", "x_mm", "y_mm", "z_mm", "sensitivity_cps_per_bq",
                         "sensitivity_cps_per_mbq", "raw_calibration_singles_count"])
        for j, source_id in enumerate(ids):
            writer.writerow([source_id, *coords[j].tolist(), sens[j], sens[j] * 1e6, raw_counts[:, j].sum()])


def _write_history_csv(path: Path, history: list[dict[str, Any]]) -> None:
    keys = ["iteration", "relative_change", "activity_sum_bq", "predicted_count_sum", "unobservable_voxels"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(history)


def run(config_path: Path) -> dict[str, Any]:
    with config_path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    base = config_path.parent
    input_paths = {key: (base / value).resolve() for key, value in config["inputs"].items()}
    output_root = (base / config["outputs"]["root"]).resolve()
    output_dirs = {
        name: output_root / name
        for name in ("response", "sensitivity", "beam_properties", "asci", "phantom", "projection", "reconstruction", "plots", "validation")
    }
    for directory in output_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    response = load_system_response(
        input_paths["system_matrix"], input_paths["system_matrix_metadata"],
        input_paths["system_matrix_table"], input_paths["scanner_config"],
    )
    image_shape = tuple(int(d) for d in config["grid"]["image_shape"])
    if int(np.prod(image_shape)) != len(response.source_ids):
        raise ValueError("Configured image_shape product must equal the system-matrix source column count")
    matrix_rate = response.matrix_cps_per_bq
    matrix_counts = response.projection_operator_counts_per_bq
    coords = response.source_coords_mm

    np.save(output_dirs["response"] / "system_response_cps_per_bq.npy", matrix_rate)
    np.save(output_dirs["response"] / "projection_operator_counts_per_bq.npy", matrix_counts)
    np.save(output_dirs["response"] / "raw_calibration_counts.npy", response.raw_counts)
    contract = {
        "orientation": "A[i,j]: i=measurement/detector/acquisition bin; j=image/source voxel",
        "shape": list(matrix_rate.shape),
        "rate_matrix_units": "counts/(s Bq), numerically cps/Bq",
        "projection_operator_units": "counts/Bq for the configured acquisition duration",
        "projection_operator_definition": "A_counts = A_rate * acquisition_s",
        "measurement_ids": response.measurement_ids,
        "detector_ids_by_row": response.detector_ids,
        "acquisition_view_ids_by_row": response.metadata.get(
            "acquisition_view_ids", response.metadata.get("view_ids", [None] * len(response.measurement_ids))
        ),
        "source_ids_by_column": response.source_ids,
        "source_coords_mm_by_column": coords.tolist(),
        "detector_coords_mm_by_row": response.detector_coords_mm.tolist(),
        "acquisition_s": response.acquisition_s,
        "activity_bq_in_source_table": response.activity_bq,
        "raw_counts_are_calibration_observations": True,
        "raw_count_matrix_shape": list(response.raw_counts.shape),
        "source_metadata": response.metadata,
    }
    _json_dump(output_dirs["response"] / "system_response_contract.json", contract)

    sensitivity, sens_summary = calculate_sensitivity(matrix_rate, coords)
    np.save(output_dirs["sensitivity"] / "sensitivity_cps_per_bq.npy", sensitivity)
    np.save(output_dirs["sensitivity"] / "sensitivity_cps_per_mbq.npy", sensitivity * 1e6)
    np.save(output_dirs["sensitivity"] / "sensitivity_map_cps_per_bq.npy", sensitivity.reshape(image_shape))
    _write_sensitivity_csv(
        output_dirs["sensitivity"] / "sensitivity_by_voxel.csv", response.source_ids,
        coords, sensitivity, response.raw_counts,
    )
    sens_summary.update({
        "units": "cps/Bq",
        "central_cps_per_mbq": sens_summary["central"] * 1e6,
        "mean_cps_per_mbq": sens_summary["mean"] * 1e6,
        "minimum_cps_per_mbq": sens_summary["minimum"] * 1e6,
        "maximum_cps_per_mbq": sens_summary["maximum"] * 1e6,
        "raw_calibration_singles_count_sum": float(response.raw_counts.sum()),
        "raw_count_interpretation": "observed singles used to form the response calibration; not a spatial sensitivity map",
    })
    _json_dump(output_dirs["sensitivity"] / "sensitivity_summary.json", sens_summary)

    response_settings = config["response"]
    regions = extract_response_regions(
        matrix_rate, coords, response.detector_coords_mm,
        relative_threshold=float(response_settings["relative_threshold"]),
        plane_axes=tuple(response_settings["angular_plane_axes"]),
    )
    np.save(output_dirs["beam_properties"] / "response_region_mask.npy", regions["mask"])
    fwhm = calculate_response_fwhm(
        matrix_rate, coords, axis=int(response_settings["fwhm_axis"]),
        minimum_samples=int(response_settings["fwhm_minimum_samples"]),
    )
    for index, item in enumerate(fwhm):
        item.update({
            "measurement_id": response.measurement_ids[index],
            "detector_id": response.detector_ids[index],
            "acquisition_view_id": contract["acquisition_view_ids_by_row"][index],
            "response_peak_cps_per_bq": float(regions["peak"][index]),
            "response_voxel_ids": [response.source_ids[j] for j in np.flatnonzero(regions["mask"][index])],
            "view_angle_deg": float(regions["angle_deg"][index]) if np.isfinite(regions["angle_deg"][index]) else None,
        })
    centroids_json = [
        [float(value) if np.isfinite(value) else None for value in row]
        for row in regions["centroid_mm"]
    ]
    _json_dump(output_dirs["beam_properties"] / "beam_properties.json", {
        "relative_response_threshold": float(response_settings["relative_threshold"]),
        "response_peak_per_measurement": regions["peak"].tolist(),
        "response_centroid_mm": centroids_json,
        "view_angle_deg": [float(v) if np.isfinite(v) else None for v in regions["angle_deg"]],
        "response_mask_voxel_count": regions["mask"].sum(axis=1).astype(int).tolist(),
        "fwhm_profiles": fwhm,
        "fwhm_method": "marginal spatial response profile with linear interpolation at half-maximum crossings",
    })

    asci_result = calculate_asci(
        regions["mask"], regions["angle_deg"], angular_bins=int(response_settings["angular_bins"])
    )
    np.save(output_dirs["asci"] / "angular_bin_occupancy.npy", asci_result["occupancy"])
    np.save(output_dirs["asci"] / "asci_fraction_by_voxel.npy", asci_result["fraction"])
    asci_summary = dict(asci_result["summary"])
    asci_summary["voxel_ids"] = response.source_ids
    asci_summary["view_angles_deg"] = [float(v) if np.isfinite(v) else None for v in regions["angle_deg"]]
    asci_summary["method"] = "fraction of configured angular bins with at least one thresholded response covering each voxel"
    _json_dump(output_dirs["asci"] / "asci_summary.json", asci_summary)

    valid_widths = [float(item["fwhm_mm"]) for item in fwhm if item["valid"]]
    ji = calculate_ji(sens_summary["mean"], valid_widths, float(asci_summary["mean_percent"]))
    _json_dump(output_dirs["beam_properties"] / "ji.json", ji)

    phantom = make_phantom(coords, response.source_ids, image_shape, config["phantom"])
    np.save(output_dirs["phantom"] / "x_true_bq.npy", phantom["x_true"])
    np.save(output_dirs["phantom"] / "phantom_image_bq.npy", phantom["image"])
    _json_dump(output_dirs["phantom"] / "phantom_metadata.json", phantom["metadata"])

    expected = forward_project(matrix_counts, phantom["x_true"])
    noisy = poisson_measurements(expected, int(config["projection"]["poisson_seed"]))
    np.save(output_dirs["projection"] / "y_expected_counts.npy", expected)
    np.save(output_dirs["projection"] / "y_poisson_counts.npy", noisy)
    _json_dump(output_dirs["projection"] / "projection_metadata.json", {
        "equation": "y_expected = A_counts @ x_true",
        "operator_units": "counts/Bq",
        "phantom_units": "Bq/voxel",
        "measurement_units": "counts per measurement bin",
        "acquisition_s": response.acquisition_s,
        "poisson_seed": int(config["projection"]["poisson_seed"]),
        "is_measured_gate_phantom_data": False,
    })

    recon_result = mlem(
        matrix_counts, noisy, iterations=int(config["mlem"]["iterations"]),
        epsilon=float(config["mlem"]["epsilon"]),
        initial_value_bq=float(config["mlem"]["initial_value_bq"]),
        relative_change_stop=config["mlem"].get("relative_change_stop"),
    )
    raw_reconstruction = recon_result["image_bq"]
    np.save(output_dirs["reconstruction"] / "mlem_raw_image_bq.npy", raw_reconstruction.reshape(image_shape))
    np.save(output_dirs["reconstruction"] / "reconstruction_error_bq.npy",
            (raw_reconstruction - phantom["x_true"]).reshape(image_shape))
    np.save(output_dirs["reconstruction"] / "iteration_estimates_bq.npy", recon_result["iteration_estimates_bq"])
    np.save(output_dirs["reconstruction"] / "mlem_sensitivity.npy", recon_result["sensitivity"])
    _json_dump(output_dirs["reconstruction"] / "mlem_configuration.json", {
        "algorithm": "maximum-likelihood expectation-maximization",
        "equations": ["predicted=A@x", "ratio=y/max(predicted,epsilon)", "backprojection=A.T@ratio", "x_new=x*backprojection/(A.T@1)"],
        "iterations_configured": recon_result["configured_iterations"],
        "iterations_completed": recon_result["completed_iterations"],
        "epsilon": recon_result["epsilon"],
        "initial_value_bq": float(config["mlem"]["initial_value_bq"]),
        "stabilization": recon_result["stabilization"],
        "post_filter": config["mlem"].get("post_filter", {"enabled": False}),
    })
    _write_history_csv(output_dirs["reconstruction"] / "convergence_history.csv", recon_result["history"])
    _json_dump(output_dirs["reconstruction"] / "convergence_history.json", recon_result["history"])
    post_filter = config["mlem"].get("post_filter", {})
    filtered = None
    if post_filter.get("enabled", False):
        if post_filter.get("method") != "gaussian":
            raise ValueError("Enabled post-filter supports only method='gaussian'")
        filtered = gaussian_postfilter(
            raw_reconstruction.reshape(image_shape), float(post_filter["sigma_voxels"])
        )
        np.save(output_dirs["reconstruction"] / "mlem_gaussian_postfiltered_image_bq.npy", filtered)

    metrics = reconstruction_metrics(phantom["x_true"], raw_reconstruction)
    _json_dump(output_dirs["reconstruction"] / "quantitative_metrics.json", {
        "data_source": "synthetic Poisson forward projection using OneCube point-source response; not measured phantom data",
        **metrics,
    })
    plot_names = generate_imaging_plots(
        output_dirs["plots"], coords, response.detector_coords_mm, sensitivity, matrix_rate, regions["mask"], fwhm,
        asci_result["fraction"], phantom["image"], raw_reconstruction.reshape(image_shape),
        expected, noisy, recon_result["history"],
    )
    matrix_rank = int(np.linalg.matrix_rank(matrix_counts))
    identifiable = bool(
        len(response.source_ids) >= int(config["identifiability"]["minimum_spatial_voxels"])
        and matrix_counts.shape[0] >= matrix_counts.shape[1]
        and matrix_rank == matrix_counts.shape[1]
        and asci_summary["occupied_angular_bins"] >= int(config["identifiability"]["minimum_distinct_angular_bins"])
    )
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "configuration_path": str(config_path.resolve()),
        "configuration": config,
        "input_artifacts": {key: str(path) for key, path in input_paths.items()},
        "matrix_shape_measurements_by_voxels": list(matrix_rate.shape),
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "scientific_reconstruction_identifiable": identifiable,
        "measurement_matrix_rank": matrix_rank,
        "distinct_angular_bins": asci_summary["occupied_angular_bins"],
        "generated_plots": plot_names,
    }
    _json_dump(output_root / "pipeline_provenance.json", provenance)
    summary = {
        "matrix_shape": list(matrix_rate.shape),
        "sensitivity_summary": sens_summary,
        "fwhm_valid_count": len(valid_widths),
        "fwhm_measurements": len(fwhm),
        "asci_summary": asci_summary,
        "ji": ji,
        "phantom_activity_bq": float(phantom["x_true"].sum()),
        "expected_projection_counts": expected.tolist(),
        "poisson_projection_counts": noisy.tolist(),
        "mlem_completed_iterations": recon_result["completed_iterations"],
        "scientific_reconstruction_identifiable": identifiable,
        "reconstruction_metrics": metrics,
        "generated_plots": plot_names,
    }
    _json_dump(output_root / "pipeline_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config" / "imaging_config.json")
    args = parser.parse_args()
    summary = run(args.config.resolve())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
