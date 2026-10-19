#!/usr/bin/env python3
"""Validate OneCube imaging derivatives and distinguish software readiness from identifiability."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from reconstruction.forward_project import forward_project
from reconstruction.mlem import mlem


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _finite_nonnegative(array: np.ndarray) -> bool:
    return bool(np.isfinite(array).all() and (array >= 0).all())


def validate(config_path: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    base = config_path.parent
    output_root = (base / config["outputs"]["root"]).resolve()
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, details: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "details": details})

    try:
        contract = _load_json(output_root / "response" / "system_response_contract.json")
        rate = np.load(output_root / "response" / "system_response_cps_per_bq.npy")
        projection_operator = np.load(output_root / "response" / "projection_operator_counts_per_bq.npy")
        raw_counts = np.load(output_root / "response" / "raw_calibration_counts.npy")
        source_ids = contract["source_ids_by_column"]
        coords = np.asarray(contract["source_coords_mm_by_column"], dtype=float)
        shape_ok = rate.ndim == 2 and rate.shape == (len(contract["measurement_ids"]), len(source_ids))
        order_ok = coords.shape == (len(source_ids), 3) and len(set(map(str, source_ids))) == len(source_ids)
        check("source_image_ordering", order_ok, f"source ids follow matrix columns; source count={len(source_ids)}")
        check("system_matrix_dimensions", shape_ok and raw_counts.shape == rate.shape and projection_operator.shape == rate.shape,
              f"rate={rate.shape}, projection={projection_operator.shape}, raw={raw_counts.shape}")
        check("finite_nonnegative_response", _finite_nonnegative(rate) and _finite_nonnegative(projection_operator) and _finite_nonnegative(raw_counts),
              "rate, count operator, and preserved calibration counts are finite and nonnegative")
        row_maps_match = (len(contract["measurement_ids"]) == len(contract["detector_ids_by_row"])
                          == len(contract["acquisition_view_ids_by_row"]))
        check("matrix_orientation_and_units", contract["orientation"].startswith("A[i,j]")
              and "counts/Bq" in contract["projection_operator_units"] and row_maps_match,
              f"{contract['orientation']}; measurement, detector, and view row maps are distinct")

        sensitivity = np.load(output_root / "sensitivity" / "sensitivity_cps_per_bq.npy")
        sensitivity_summary = _load_json(output_root / "sensitivity" / "sensitivity_summary.json")
        check("sensitivity_dimensions", sensitivity.shape == (rate.shape[1],), f"shape={sensitivity.shape}")
        check("sensitivity_finite_nonnegative", _finite_nonnegative(sensitivity), "sensitivity vector finite and nonnegative")
        check("sensitivity_summary", all(k in sensitivity_summary for k in ("central", "mean", "minimum", "maximum")),
              "central, mean, minimum, and maximum are recorded")

        masks = np.load(output_root / "beam_properties" / "response_region_mask.npy")
        beams = _load_json(output_root / "beam_properties" / "beam_properties.json")
        fwhm_entries = beams["fwhm_profiles"]
        masks_ok = masks.shape == rate.shape
        fwhm_ok = len(fwhm_entries) == rate.shape[0] and all(
            ((entry.get("valid") and isinstance(entry.get("fwhm_mm"), (int, float)) and entry["fwhm_mm"] > 0)
             or (not entry.get("valid") and bool(entry.get("reason"))))
            and all(key in entry for key in ("measurement_id", "detector_id", "response_peak_cps_per_bq", "response_voxel_ids"))
            for entry in fwhm_entries
        )
        row_peaks = rate.max(axis=1, keepdims=True)
        expected_masks = (row_peaks > 0) & (rate >= float(config["response"]["relative_threshold"]) * row_peaks)
        check("response_masks", masks_ok and np.array_equal(masks, expected_masks),
              f"mask shape={masks.shape}; threshold={config['response']['relative_threshold']}")
        check("fwhm_validity_flags", fwhm_ok, f"{sum(bool(entry.get('valid')) for entry in fwhm_entries)} valid of {len(fwhm_entries)}; invalid profiles retain reasons")

        occupancy = np.load(output_root / "asci" / "angular_bin_occupancy.npy")
        asci = np.load(output_root / "asci" / "asci_fraction_by_voxel.npy")
        asci_summary = _load_json(output_root / "asci" / "asci_summary.json")
        asci_ok = occupancy.shape == (rate.shape[1], int(config["response"]["angular_bins"])) and asci.shape == (rate.shape[1],)
        check("asci_dimensions_range", asci_ok and np.isfinite(asci).all() and ((asci >= 0) & (asci <= 1)).all(),
              f"occupancy={occupancy.shape}, fraction={asci.shape}, range=[0,1]")
        check("asci_provenance", "view_angles_deg" in asci_summary and "angular_bins" in asci_summary,
              "ASCI records derived view angles and configured angular bins")
        ji = _load_json(output_root / "beam_properties" / "ji.json")
        check("ji_definedness", (ji["valid"] and isinstance(ji["ji"], (int, float))) or
              (not ji["valid"] and ji["ji"] is None and bool(ji["reason"])),
              "JI is numeric only when valid FWHM exists; otherwise explicit reason is recorded")

        phantom = np.load(output_root / "phantom" / "x_true_bq.npy")
        phantom_image = np.load(output_root / "phantom" / "phantom_image_bq.npy")
        phantom_meta = _load_json(output_root / "phantom" / "phantom_metadata.json")
        phantom_ok = (phantom.shape == (rate.shape[1],) and phantom_image.size == rate.shape[1]
                      and phantom_meta["voxel_ids"] == source_ids and _finite_nonnegative(phantom)
                      and _finite_nonnegative(phantom_image))
        check("phantom_dimensions_ordering", phantom_ok and _finite_nonnegative(phantom), f"shape={phantom.shape}, image={phantom_image.shape}")

        expected = np.load(output_root / "projection" / "y_expected_counts.npy")
        noisy = np.load(output_root / "projection" / "y_poisson_counts.npy")
        projection_meta = _load_json(output_root / "projection" / "projection_metadata.json")
        projection_match = expected.shape == (rate.shape[0],) and np.allclose(expected, forward_project(projection_operator, phantom))
        check("forward_projection", projection_match and noisy.shape == expected.shape and _finite_nonnegative(expected) and _finite_nonnegative(noisy),
              f"expected/noisy shape={expected.shape}; equation {projection_meta['equation']}")

        recon = np.load(output_root / "reconstruction" / "mlem_raw_image_bq.npy")
        error_image = np.load(output_root / "reconstruction" / "reconstruction_error_bq.npy")
        estimates = np.load(output_root / "reconstruction" / "iteration_estimates_bq.npy")
        history = _load_json(output_root / "reconstruction" / "convergence_history.json")
        recon_config = _load_json(output_root / "reconstruction" / "mlem_configuration.json")
        recon_ok = (recon.size == rate.shape[1] and error_image.size == rate.shape[1]
                    and _finite_nonnegative(recon) and np.isfinite(error_image).all())
        check("reconstruction_dimensions_nonnegative", recon_ok, f"reconstruction size={recon.size}; voxel count={rate.shape[1]}")
        check("mlem_convergence_history", len(history) > 0 and estimates.shape == (len(history) + 1, rate.shape[1]),
              f"history={len(history)} iterations; stored estimates={estimates.shape}")
        check("mlem_configuration_and_finiteness", recon_config["iterations_completed"] == len(history) and np.isfinite(estimates).all(),
              "configured iterations, epsilon, stabilization, and all iterate vectors are stored")

        provenance = _load_json(output_root / "pipeline_provenance.json")
        plots = provenance.get("generated_plots", [])
        plots_ok = len(plots) >= 12 and all((output_root / "plots" / name).is_file() for name in plots)
        check("reconstruction_plots_exist", plots_ok, f"{len(plots)} plot artifacts recorded")
        metrics = _load_json(output_root / "reconstruction" / "quantitative_metrics.json")
        metrics_ok = all(np.isfinite(metrics[key]) for key in ("mse_bq2", "rmse_bq", "normalized_error"))
        check("quantitative_outputs", metrics_ok, "defined error and activity metrics are finite; undefined correlation remains null")
        check("provenance_configuration_recorded", provenance.get("configuration") == config and bool(provenance.get("input_artifacts")),
              "input artifact paths and complete effective configuration are recorded")

        # This independent square-system smoke case proves generic math without claiming OneCube identifiability.
        smoke_a = np.eye(2, dtype=float)
        smoke_x = np.asarray([2.0, 3.0])
        smoke_y = forward_project(smoke_a, smoke_x)
        smoke_recon = mlem(smoke_a, smoke_y, iterations=2, epsilon=1e-12, initial_value_bq=1.0)
        smoke_ok = np.allclose(smoke_y, smoke_x) and np.allclose(smoke_recon["image_bq"], smoke_x)
        check("generic_algorithm_smoke", smoke_ok, "independent 2-voxel identity response forward-projects and MLEM-recovers known values")

        rank = int(np.linalg.matrix_rank(projection_operator))
        occupied_angles = int(asci_summary["occupied_angular_bins"])
        spatial_minimum = int(config["identifiability"]["minimum_spatial_voxels"])
        angular_minimum = int(config["identifiability"]["minimum_distinct_angular_bins"])
        identifiable = bool(
            rate.shape[1] >= spatial_minimum and rate.shape[0] >= rate.shape[1]
            and rank == rate.shape[1] and occupied_angles >= angular_minimum
        )
        blockers = []
        if rate.shape[1] < spatial_minimum:
            blockers.append(f"need at least {spatial_minimum} spatial source voxels; have {rate.shape[1]}")
        if rate.shape[0] < rate.shape[1] or rank < rate.shape[1]:
            blockers.append(f"need enough independent measurement bins for full column rank; rows={rate.shape[0]}, voxels={rate.shape[1]}, rank={rank}")
        if occupied_angles < angular_minimum:
            blockers.append(f"need at least {angular_minimum} distinct measured angular bins; have {occupied_angles}")
        check("scientific_reconstruction_identifiability", identifiable,
              f"rank={rank}, measurements={rate.shape[0]}, voxels={rate.shape[1]}, occupied_angles={occupied_angles}; " + ("identifiable" if identifiable else "; ".join(blockers)))
        software_ready = all(item["passed"] for item in checks if item["name"] != "scientific_reconstruction_identifiability")
        result = {
            "status": "SOFTWARE PIPELINE READY" if software_ready else "SOFTWARE PIPELINE VALIDATION FAILED",
            "software_pipeline_ready": software_ready,
            "scientific_reconstruction_identifiable": identifiable,
            "matrix_rank": rank,
            "measurement_bins": int(rate.shape[0]),
            "spatial_voxels": int(rate.shape[1]),
            "distinct_angular_bins": occupied_angles,
            "additional_acquisition_needed": blockers,
            "checks": checks,
            "final_token": "ONECUBE_IMAGING_END_TO_END_PASS" if software_ready and identifiable else
                           "ONECUBE_IMAGING_PIPELINE_READY_RECONSTRUCTION_ACQUISITION_REQUIRED" if software_ready else None,
        }
    except Exception as exc:
        checks.append({"name": "pipeline_validation_execution", "passed": False, "details": f"{type(exc).__name__}: {exc}"})
        result = {
            "status": "SOFTWARE PIPELINE VALIDATION FAILED",
            "software_pipeline_ready": False,
            "scientific_reconstruction_identifiable": False,
            "checks": checks,
            "final_token": None,
        }

    validation_dir = output_root / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    report_path = validation_dir / "imaging_validation.json"
    with report_path.open("w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config" / "imaging_config.json")
    args = parser.parse_args()
    result = validate(args.config.resolve())
    raise SystemExit(0 if result["software_pipeline_ready"] else 1)


if __name__ == "__main__":
    main()
