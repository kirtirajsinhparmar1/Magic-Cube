#!/usr/bin/env python3
"""Validate static preparation or completed Gate-derived imaging outputs."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from onecube_imaging.design import d4_representatives, make_phantom, make_poses, make_voxels
from onecube_imaging.io import file_sha256, load_config, read_csv, write_runtime_json


def _check(checks: list[dict[str, Any]], name: str, passed: bool, details: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "details": details})


def _all_finite(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if isinstance(value, (int, float, np.number)):
        return math.isfinite(float(value))
    if isinstance(value, (list, tuple)):
        return all(_all_finite(item) for item in value)
    if isinstance(value, dict):
        return all(_all_finite(item) for item in value.values())
    return False


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_slurm_submission_scripts(checks: list[dict[str, Any]]) -> None:
    launcher = PROJECT_ROOT / "slurm/par_imaging_full.sh"
    if not launcher.is_file() or not os.access(launcher, os.R_OK):
        _check(checks, "slurm_submission_scripts", False,
               f"launcher is missing or unreadable: {launcher}")
        return

    try:
        text = launcher.read_text(encoding="utf-8")
    except OSError as error:
        _check(checks, "slurm_submission_scripts", False,
               f"cannot read launcher {launcher}: {error}")
        return

    root_match = re.search(r'(?m)^PROJECT_ROOT="([^"]+)"$', text)
    slurm_dir_is_rooted = bool(re.search(r'(?m)^SLURM_DIR="\$PROJECT_ROOT/slurm"$', text))
    root_is_absolute_project = bool(
        root_match and Path(root_match.group(1)) == PROJECT_ROOT.resolve()
    )
    commands = re.findall(
        r'(?ms)^[A-Za-z_][A-Za-z0-9_]*_id="\$\(sbatch\b(.*?)\)"\s*$', text
    )
    sbatch_count = len(re.findall(r"\bsbatch\s+--parsable\b", text))
    referenced: list[str] = []
    issues: list[str] = []
    if not root_is_absolute_project:
        issues.append("launcher PROJECT_ROOT is not the absolute OneCubeImagingFinal path")
    if not slurm_dir_is_rooted:
        issues.append("SLURM_DIR is not derived from PROJECT_ROOT/slurm")
    if sbatch_count != len(commands):
        issues.append(f"found {sbatch_count} sbatch references but parsed {len(commands)} submissions")

    for index, command in enumerate(commands, start=1):
        names = re.findall(r'"\$SLURM_DIR/([^"/]+\.slurm)"', command)
        if len(names) != 1:
            issues.append(f"submission {index} does not reference exactly one quoted SLURM_DIR worker")
            continue
        referenced.append(names[0])

    worker_array = re.search(r"(?ms)^SLURM_WORKERS=\((.*?)^\)", text)
    preflight_present = bool(
        worker_array
        and re.search(r'for worker_script in "\$\{SLURM_WORKERS\[@\]\}"; do', text)
        and '[[ ! -f "$worker_script" || ! -r "$worker_script" ]]' in text
    )
    preflight_names = (
        re.findall(r'"\$SLURM_DIR/([^"/]+\.slurm)"', worker_array.group(1))
        if worker_array else []
    )
    if not preflight_present:
        issues.append("missing readable-file preflight for the required worker list")
    if set(preflight_names) != set(referenced):
        issues.append(
            f"preflight workers {sorted(set(preflight_names))} differ from submitted workers {sorted(set(referenced))}"
        )

    slurm_dir = PROJECT_ROOT / "slurm"
    missing = [
        str(slurm_dir / name)
        for name in sorted(set(referenced))
        if not (slurm_dir / name).is_file() or not os.access(slurm_dir / name, os.R_OK)
    ]
    if missing:
        issues.append(f"submitted workers are missing or unreadable: {missing}")

    _check(checks, "slurm_submission_scripts", not issues,
           f"all {len(commands)} sbatch submissions use quoted absolute-project Slurm paths; "
           f"workers={sorted(set(referenced))}"
           if not issues else "; ".join(issues))


def _preparation_validation(config: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    _validate_slurm_submission_scripts(checks)
    prep_path = PROJECT_ROOT / "runtime/provenance/preparation_manifest.json"
    try:
        preparation = _read_json(prep_path)
    except Exception as error:
        preparation = {}
        _check(checks, "preparation_provenance", False, f"cannot read preparation manifest: {error}")
    if preparation:
        _check(checks, "preparation_provenance", not preparation.get("runtime_executed", True),
               "preparation provenance exists and makes no runtime claim")
        _check(checks, "configuration_hash", preparation.get("config_sha256") == file_sha256(
            PROJECT_ROOT / "config/imaging_config.json"
        ), "preparation configuration hash matches the current single imaging configuration")
        baseline = Path(preparation.get("baseline_project", ""))
        hashes = preparation.get("baseline_macro_sha256", {})
        unchanged = bool(hashes)
        changed_assets = []
        for relative_path, expected in hashes.items():
            source = baseline / relative_path
            if not source.is_file() or file_sha256(source) != expected:
                unchanged = False
                changed_assets.append(relative_path)
        _check(checks, "frozen_baseline_unchanged", unchanged,
               "all reused OneCube macro/material assets match preparation hashes"
               if unchanged else f"changed or missing frozen assets: {changed_assets}")

    try:
        voxels = read_csv(PROJECT_ROOT / "runtime/manifests/image_voxel_map.csv")
        poses = read_csv(PROJECT_ROOT / "runtime/manifests/acquisition_poses.csv")
        rows = read_csv(PROJECT_ROOT / "runtime/manifests/measurement_row_map.csv")
        calibration = read_csv(PROJECT_ROOT / "runtime/manifests/response_simulation_manifest.csv")
        phantom_tasks = read_csv(PROJECT_ROOT / "runtime/manifests/phantom_acquisition_manifest.csv")
        phantom_sources = read_csv(PROJECT_ROOT / "runtime/manifests/phantom_voxel_sources.csv")
    except Exception as error:
        voxels, poses, rows, calibration, phantom_tasks, phantom_sources = [], [], [], [], [], []
        _check(checks, "manifests_readable", False, str(error))

    expected_voxels = make_voxels(config)
    expected_poses = make_poses(config)
    _check(checks, "image_voxel_ordering",
           len(voxels) == len(expected_voxels)
           and [(int(v["voxel_id"]), int(v["x_index"]), int(v["y_index"])) for v in voxels]
           == [(int(v["voxel_id"]), v["x_index"], v["y_index"]) for v in expected_voxels],
           f"voxel ordering is row-major y then x; found {len(voxels)} columns")
    pose_keys = [(int(p["pose_id"]), int(p["row_id"])) for p in poses]
    row_keys = [(int(p["pose_id"]), int(p["row_id"])) for p in rows]
    expected_pose_keys = [(p["pose_id"], p["row_id"]) for p in expected_poses]
    _check(checks, "physical_measurement_row_ordering",
           len(poses) == len(expected_poses) and pose_keys == expected_pose_keys
           and row_keys == expected_pose_keys and len({(r["detector_x_mm"], r["detector_y_mm"]) for r in rows}) == len(rows),
           f"{len(rows)} distinct physical detector poses map one-to-one to measurement rows")
    expected_offsets = d4_representatives(int(config["acquisition"]["max_relative_offset_index"]))
    observed_offsets = [(int(row["offset_dx_index"]), int(row["offset_dy_index"])) for row in calibration]
    _check(checks, "measured_relative_offset_coverage",
           observed_offsets == expected_offsets and len(calibration) == int(config["resources"]["calibration_tasks"]),
           f"{len(calibration)} direct Gate calibration conditions cover the complete D4 quotient grid")
    _check(checks, "phantom_acquisition_manifest",
           len(phantom_tasks) == len(rows) == int(config["resources"]["phantom_tasks"])
           and [int(task["row_id"]) for task in phantom_tasks] == list(range(len(rows))),
           f"{len(phantom_tasks)} independent Gate phantom exposures map in physical row order")
    try:
        activity = np.asarray([float(row["activity_Bq"]) for row in phantom_sources])
        total_activity = float(config["phantom"]["total_activity_Bq"])
        valid_phantom = (
            activity.size == len(voxels) and np.isfinite(activity).all()
            and np.all(activity > 0) and np.isclose(activity.sum(), total_activity, rtol=1e-12)
            and np.unique(activity).size > 1
        )
    except Exception:
        valid_phantom = False
        activity = np.asarray([])
        total_activity = float(config["phantom"]["total_activity_Bq"])
    _check(checks, "multi_voxel_phantom_distribution", valid_phantom,
           f"{activity.size} positive voxel sources sum to {total_activity:g} Bq and contain spatial activity variation")

    macro_errors = []
    project_prefix = str(PROJECT_ROOT.resolve())
    for task in calibration + phantom_tasks:
        macro = PROJECT_ROOT / task["macro_path"]
        if not macro.is_file():
            macro_errors.append(f"missing {macro}")
            continue
        text = macro.read_text(encoding="utf-8")
        for key in ("root_base_path", "singles_root_path", "hits_root_path"):
            output_path = (PROJECT_ROOT / task[key]).resolve()
            if not str(output_path).startswith(project_prefix + "/"):
                macro_errors.append(f"output escapes new project for task {task['task_id']}: {output_path}")
        if "/gate/geometry/setMaterialDatabase GateMaterials.db" not in text:
            macro_errors.append(f"task {task['task_id']} does not use the frozen local material database")
        if "/gate/random/setEngineSeed " not in text or "/gate/application/startDAQ" not in text:
            macro_errors.append(f"task {task['task_id']} lacks a deterministic seed or DAQ command")
        if "/gate/output/tree/addCollection Singles" not in text or "/gate/output/tree/hits/enable" not in text:
            macro_errors.append(f"task {task['task_id']} lacks the validated ROOT Hits/Singles output")
    _check(checks, "isolated_gate_task_macros", not macro_errors,
           "all generated macros reuse frozen geometry/physics and write outputs only below OneCubeImagingFinal"
           if not macro_errors else "; ".join(macro_errors[:5]))
    workers = int(config["resources"]["gate_workers"])
    aggregate_mem = workers * int(config["resources"]["memory_per_worker_gb"])
    _check(checks, "conservative_worker_resources",
           1 <= workers <= 4 and workers * int(config["resources"]["cpus_per_worker"]) <= 16 and aggregate_mem <= 40,
           f"{workers} workers, {workers * int(config['resources']['cpus_per_worker'])} CPUs, {aggregate_mem} GB aggregate memory")
    expected_histories = (
        len(calibration) * float(config["acquisition"]["calibration_activity_Bq"]) * float(config["acquisition"]["calibration_exposure_s"])
        + len(phantom_tasks) * float(config["phantom"]["total_activity_Bq"]) * float(config["acquisition"]["phantom_exposure_s"])
    )
    _check(checks, "planned_monte_carlo_scale",
           math.isclose(expected_histories, float(config["resources"]["estimated_primary_histories"]), rel_tol=0, abs_tol=1)
           and math.isclose(expected_histories / (
               float(config["baseline"]["source_activity_Bq"]) * float(config["baseline"]["baseline_acquisition_s"])
           ), float(config["resources"]["baseline_exposure_equivalents"]), rel_tol=0, abs_tol=1e-8),
           f"{expected_histories:,.0f} planned primaries ({expected_histories / 3.7e6:.0f} validated 1 s baseline exposure equivalents)")
    required_outputs = [
        PROJECT_ROOT / "ONECUBE_IMAGING_FINAL_REPORT.md",
        PROJECT_ROOT / "results/plots/acquisition_design.png",
        PROJECT_ROOT / "results/plots/phantom_design.png",
        PROJECT_ROOT / "runtime/provenance/preparation_figures.json",
    ]
    missing_outputs = [str(path) for path in required_outputs if not path.is_file()]
    _check(checks, "preparation_outputs_exist", not missing_outputs,
           "report and acquisition/phantom design figures exist" if not missing_outputs else str(missing_outputs))
    passed = all(check["passed"] for check in checks)
    result = {
        "status": "STATIC PREPARATION PASS" if passed else "STATIC PREPARATION FAILED",
        "software_pipeline_ready": passed,
        "scientific_reconstruction_identifiable": None,
        "measurement_bins": len(rows),
        "spatial_voxels": len(voxels),
        "calibration_conditions": len(calibration),
        "phantom_gate_tasks": len(phantom_tasks),
        "production_runtime_executed": False,
        "checks": checks,
        "final_token": "ONECUBE_IMAGING_FULL_PREPARATION_PASS" if passed else None,
    }
    write_runtime_json(PROJECT_ROOT / "results/validation/preparation_validation.json", result)
    return result


def _runtime_validation(config: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    calibration = read_csv(PROJECT_ROOT / "runtime/manifests/response_simulation_manifest.csv")
    phantom_tasks = read_csv(PROJECT_ROOT / "runtime/manifests/phantom_acquisition_manifest.csv")
    rows = read_csv(PROJECT_ROOT / "runtime/manifests/measurement_row_map.csv")
    voxels = read_csv(PROJECT_ROOT / "runtime/manifests/image_voxel_map.csv")
    task_failures = []
    for stage, tasks in (("calibration", calibration), ("phantom", phantom_tasks)):
        for task in tasks:
            task_id = int(task["task_id"])
            completion = PROJECT_ROOT / f"runtime/{stage}/completions/task_{task_id:03d}.json"
            if not completion.is_file():
                task_failures.append(f"{stage}:{task_id} completion missing")
                continue
            record = _read_json(completion)
            if record.get("status") != "completed" or int(record.get("gate_exit_status", -1)) != 0:
                task_failures.append(f"{stage}:{task_id} not successful")
    _check(checks, "all_gate_tasks_completed", not task_failures,
           f"{len(calibration)} calibration and {len(phantom_tasks)} phantom task records complete"
           if not task_failures else "; ".join(task_failures[:8]))
    required_arrays = {
        "rate": PROJECT_ROOT / "results/system_matrix/rate_response_cps_per_bq.npy",
        "operator": PROJECT_ROOT / "results/system_matrix/count_operator_counts_per_bq.npy",
        "raw": PROJECT_ROOT / "results/system_matrix/raw_counts_symmetry_expanded.npy",
        "ppdf": PROJECT_ROOT / "results/system_matrix/row_normalized_ppdf.npy",
        "sensitivity": PROJECT_ROOT / "results/sensitivity/sensitivity_cps_per_bq.npy",
        "sensitivity_map_cps_per_mbq": PROJECT_ROOT / "results/sensitivity/sensitivity_map_cps_per_mbq.npy",
        "mask": PROJECT_ROOT / "results/system_matrix/response_masks.npy",
        "truth": PROJECT_ROOT / "results/phantom/phantom_activity_bq.npy",
        "expected": PROJECT_ROOT / "results/projections/expected_counts.npy",
        "poisson": PROJECT_ROOT / "results/projections/synthetic_poisson_counts.npy",
        "gate_y": PROJECT_ROOT / "results/projections/independent_gate_singles_counts.npy",
        "gate_x": PROJECT_ROOT / "results/reconstruction/independent_gate_mlem_activity_bq.npy",
        "synthetic_x": PROJECT_ROOT / "results/reconstruction/synthetic_mlem_activity_bq.npy",
    }
    arrays: dict[str, np.ndarray] = {}
    absent = []
    for key, path in required_arrays.items():
        if path.is_file():
            arrays[key] = np.load(path)
        else:
            absent.append(str(path))
    _check(checks, "runtime_artifacts_present", not absent,
           "system, sensitivity, phantom, projection, and reconstruction arrays exist"
           if not absent else f"missing arrays: {absent}")
    matrix_shape_ok = finite_nonnegative = False
    diagnostics: dict[str, Any] = {}
    if len(arrays) == len(required_arrays):
        expected_shape = (len(rows), len(voxels))
        matrix_shape_ok = arrays["rate"].shape == expected_shape and arrays["operator"].shape == expected_shape and arrays["raw"].shape == expected_shape
        _check(checks, "system_matrix_dimensions", matrix_shape_ok,
               f"R, H, raw arrays expected {expected_shape}; R={arrays['rate'].shape}, H={arrays['operator'].shape}, raw={arrays['raw'].shape}")
        finite_nonnegative = all(np.isfinite(arrays[key]).all() and np.all(arrays[key] >= 0) for key in arrays)
        _check(checks, "runtime_arrays_finite_nonnegative", finite_nonnegative,
               "all runtime response, sensitivity, phantom, projection, and reconstruction arrays are finite and nonnegative")
        _check(checks, "derived_dimensions",
               arrays["sensitivity"].shape == (len(voxels),)
               and arrays["sensitivity_map_cps_per_mbq"].shape == tuple(config["image"][key] for key in ("ny", "nx"))
               and arrays["mask"].shape == expected_shape
               and arrays["truth"].shape == (len(voxels),)
               and arrays["expected"].shape == (len(rows),)
               and arrays["poisson"].shape == (len(rows),)
               and arrays["gate_y"].shape == (len(rows),)
               and arrays["gate_x"].shape == (len(voxels),)
               and arrays["synthetic_x"].shape == (len(voxels),),
               "sensitivity vectors/maps, masks, phantom, measurements, and reconstructions match row/voxel maps")
        expected_operator = arrays["rate"] * float(config["acquisition"]["phantom_exposure_s"])
        _check(checks, "response_units_and_count_operator",
               np.allclose(arrays["operator"], expected_operator, rtol=1e-12, atol=0),
               "H = R × configured phantom exposure; R is cps/Bq and H is expected counts/Bq")
        zero_rows = arrays["rate"].sum(axis=1) == 0
        ppdf_sums = arrays["ppdf"].sum(axis=1)
        _check(checks, "ppdf_normalization",
               np.allclose(ppdf_sums[~zero_rows], 1.0, atol=1e-10) and np.all(ppdf_sums[zero_rows] == 0),
               "nonzero response rows sum to one; zero rows remain explicitly zero")
        _check(checks, "independent_gate_measurement_counts",
               np.all(arrays["gate_y"] >= 0) and np.all(arrays["gate_y"] == np.floor(arrays["gate_y"])),
               "y_gate consists of nonnegative integer Singles counts")
    for name, relative in (
        ("fwhm", "results/fwhm/fwhm_summary.json"),
        ("asci", "results/asci/asci_applicability.json"),
        ("ji", "results/asci/ji_result.json"),
        ("diagnostics", "results/system_matrix/information_diagnostics.json"),
        ("synthetic_metrics", "results/reconstruction/synthetic_metrics.json"),
        ("gate_metrics", "results/reconstruction/independent_gate_metrics.json"),
        ("synthetic_history", "results/reconstruction/synthetic_mlem_history.json"),
        ("gate_history", "results/reconstruction/independent_gate_mlem_history.json"),
    ):
        path = PROJECT_ROOT / relative
        if not path.is_file():
            _check(checks, f"{name}_record", False, f"missing {path}")
            continue
        record = _read_json(path)
        _check(checks, f"{name}_finite", _all_finite(record), f"{relative} contains only finite values or explicit nulls")
        if name == "fwhm":
            profile_rows = record.get("measurements", [])
            valid_shape = len(profile_rows) == len(rows) and all("valid" in item for item in profile_rows)
            _check(checks, "fwhm_validity_flags", valid_shape,
                   f"{sum(bool(item.get('valid')) for item in profile_rows)} valid of {len(profile_rows)} response rows; invalid crossings retain reasons")
        elif name == "asci":
            _check(checks, "asci_physical_applicability",
                   record.get("defined") is False and record.get("status") == "NOT PHYSICALLY APPLICABLE",
                   f"ASCI applicability is explicitly recorded: {record.get('reason')}")
        elif name == "ji":
            _check(checks, "ji_definedness",
                   (record.get("valid") is True and record.get("ji") is not None)
                   or (record.get("valid") is False and record.get("ji") is None and record.get("reason")),
                   "JI is numeric only when its measured sensitivity, valid FWHM, and physical ASCI inputs are defined")
        elif name == "diagnostics":
            diagnostics = record
            _check(checks, "matrix_information_diagnostics",
                   record.get("matrix_shape") == [len(rows), len(voxels)]
                   and record.get("singular_values") is not None,
                   "rank, singular values, conditioning, and zero-sensitivity voxel diagnostics exist")
        elif name.endswith("history"):
            history = record
            configured = int(config["reconstruction"]["iterations"])
            _check(checks, f"{name}_iterations",
                   history.get("completed_iterations") == configured
                   and len(history.get("estimate_history_bq", [])) == configured + 1
                   and len(history.get("poisson_log_likelihood", [])) == configured + 1,
                   f"all {configured} configured MLEM iterations and the initial estimate are preserved")
    plot_record_path = PROJECT_ROOT / "runtime/provenance/reconstruction.json"
    plots_ok = False
    if plot_record_path.is_file():
        plot_record = _read_json(plot_record_path)
        plots = plot_record.get("generated_plots", [])
        plots_ok = bool(plots) and all((PROJECT_ROOT / path).is_file() for path in plots)
    _check(checks, "scientific_figures_exist", plots_ok,
           "system, response, FWHM, projection, reconstruction, and convergence figures are recorded and present")
    prep_provenance = PROJECT_ROOT / "runtime/provenance/preparation_manifest.json"
    runtime_provenance = PROJECT_ROOT / "runtime/provenance/reconstruction.json"
    _check(checks, "configuration_and_provenance",
           prep_provenance.is_file() and runtime_provenance.is_file()
           and (PROJECT_ROOT / "results/validation/preparation_validation.json").is_file(),
           "effective configuration, input hashes, task provenance, and preparation validation are present")
    rank = int(diagnostics.get("numerical_rank", 0))
    condition = diagnostics.get("condition_number_on_retained_subspace")
    condition_limit = float(config["analysis"]["numerical_identifiability_condition_screen"])
    zero_voxels = diagnostics.get("zero_sensitivity_voxel_ids", list(range(len(voxels))))
    identifiable = (
        rank == len(voxels) and not zero_voxels and condition is not None
        and math.isfinite(float(condition)) and float(condition) <= condition_limit
    )
    passed = all(check["passed"] for check in checks)
    result = {
        "status": (
            "SOFTWARE PIPELINE COMPLETE; LINEAR IDENTIFIABILITY SCREEN PASSED"
            if passed and identifiable else
            "SOFTWARE PIPELINE COMPLETE; SCIENTIFIC IDENTIFIABILITY LIMITED"
            if passed else "RUNTIME PIPELINE VALIDATION FAILED"
        ),
        "software_pipeline_ready": passed,
        "independent_gate_measurements_complete": not task_failures,
        "scientific_reconstruction_identifiable": bool(identifiable),
        "identifiability_definition": "full voxel-column rank at configured SVD tolerance, no zero-sensitivity voxel, and retained-subspace condition number not exceeding configured screen; this is not a reconstruction-quality guarantee",
        "condition_number_screen": condition_limit,
        "matrix_rank": rank,
        "measurement_bins": len(rows),
        "spatial_voxels": len(voxels),
        "condition_number": condition,
        "checks": checks,
        "scientific_acceptance": "requires review of independent Gate reconstruction, projection residuals, spatial recovery metrics, and uncertainty; software validation alone does not establish acceptance",
    }
    write_runtime_json(PROJECT_ROOT / "results/validation/runtime_validation.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("prepare", "runtime"), default="prepare")
    args = parser.parse_args()
    config = load_config(PROJECT_ROOT)
    try:
        result = (
            _preparation_validation(config) if args.stage == "prepare"
            else _runtime_validation(config)
        )
    except Exception as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["software_pipeline_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
