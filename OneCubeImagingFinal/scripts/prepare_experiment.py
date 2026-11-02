#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from onecube_imaging.design import d4_representatives, make_phantom, make_poses, make_voxels
from onecube_imaging.io import file_sha256, load_config, save_npy, write_csv, write_generated_text, write_json
from reconstruction.phantom import source_rows
from visualization.imaging_plots import render_preparation


def _macro_header(config: dict, baseline: Path, pose_x: float, pose_y: float) -> list[str]:
    acquisition = config["acquisition"]
    return [
        "# Generated task macro using frozen OneCube geometry, physics, and digitizer assets.",
        "/gate/geometry/setMaterialDatabase GateMaterials.db",
        "/control/execute geometry.mac",
        "/control/execute plate.mac",
        "/control/execute system.mac",
        "/control/execute physics.mac",
        f"/gate/cylindricalPET/placement/setTranslation {pose_x:.6f} {pose_y:.6f} {float(acquisition['detector_z_mm']):.6f} mm",
        "/gate/run/initialize",
        "/control/execute digitizer.mac",
    ]


def _source_block(name: str, source: dict, energy_keV: float) -> list[str]:
    return [
        f"/gate/source/addSource {name}",
        f"/gate/source/{name}/gps/particle gamma",
        f"/gate/source/{name}/gps/pos/type Point",
        f"/gate/source/{name}/gps/pos/centre {float(source['x_mm']):.8f} {float(source['y_mm']):.8f} {float(source['z_mm']):.8f} mm",
        f"/gate/source/{name}/gps/ang/type iso",
        f"/gate/source/{name}/gps/ene/type Mono",
        f"/gate/source/{name}/gps/ene/mono {energy_keV:.6f} keV",
        f"/gate/source/{name}/setActivity {float(source['activity_Bq']):.12g} Bq",
    ]


def _write_macro(
    path: Path,
    config: dict,
    baseline: Path,
    detector_x: float,
    detector_y: float,
    seed: int,
    output_base: Path,
    sources: list[dict],
    exposure_s: float,
) -> None:
    lines = _macro_header(config, baseline, detector_x, detector_y)
    for index, source in enumerate(sources):
        lines.extend(_source_block(f"source_{index:03d}", source, float(config["baseline"]["source_energy_keV"])))
    lines.extend([
        "/gate/source/list",
        "/gate/random/setEngineName MersenneTwister",
        f"/gate/random/setEngineSeed {seed}",
        "/control/execute verbose.mac",
        "/gate/output/tree/enable",
        f"/gate/output/tree/addFileName {output_base}",
        "/gate/output/tree/hits/enable",
        "/gate/output/tree/addCollection Singles",
        "/gate/application/setTimeStart 0 s",
        f"/gate/application/setTimeStop {exposure_s:.8g} s",
        "/gate/application/setTimeSlice 1 s",
        "/gate/application/startDAQ",
        "",
    ])
    write_generated_text(path, "\n".join(lines))


def _report_text(config: dict, calibration_tasks: int, phantom_tasks: int, histories: int) -> str:
    launch_fence = chr(96) * 3
    return f"""# OneCube Imaging Final — Preparation and Runtime Results

## Preparation status

Static preparation is complete. The full GATE imaging experiment has not run. This report contains no measured response matrix, sensitivity map, FWHM result, reconstruction, or Monte Carlo acceptance claim yet.

## Frozen OneCube baseline

The new project consumes validated assets in the sibling OneCube directory without changing them: one 2×2×2 mm GAGG crystal (detector ID 0), centered at the origin, a 140 keV isotropic source at z = -51 mm, 3.7 MBq, and a 50 mm center-pose surface gap. The baseline recorded 233 Hits and 233 Singles in one second, corresponding to about 62.97 cps/MBq. Existing geometry, digitizer, physics, and ROOT output macros are included at run time; new output paths point only into this project.

## Reference methodology

The Small-Animal-Imaging-SPECT repository was consulted only for mathematical procedures: row/voxel response interpretation, threshold-derived response regions, line-profile FWHM by half-height crossings, angular-bin occupancy for ASCI, JI, forward projection, and multiplicative MLEM with likelihood/convergence plots. Relevant sources: [PPDF interpretation](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/arg_ppdf_t8.py), [response masks](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/arg_extract_beam_masks.py), [beam properties and FWHM](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/beam_property_extract.py), [ASCI filtering](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/arg_analyze_extracted_properties.py), [ASCI mapping](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/asci_plot_generation.py), [JI](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/6_calc_ji.py), [projection](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/projection_t8.py), and [MLEM](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/mlem_torch_gpf_nonmpi.py). The calculations were independently implemented for OneCube row and voxel maps.

## Geometry isolation

No SAI geometry, detector layout, source position, FOV, pixel grid, attenuation model, numerical result, or geometry-generation code was transferred. Only OneCube frozen Gate macros define the physical geometry. The new project translates the existing detector hierarchy as one rigid body and places sources in its own image plane.

## Final acquisition design

The image is a 7×7, 35×35 mm sampled plane at z = -51 mm with 5 mm voxel pitch. The matching physical scan translates the single crystal through 49 XY poses on the same 5 mm grid at z = 0, with fixed orientation. At the center pose the validated 50 mm crystal-surface gap is preserved. Each translated detector pose is one actual independent exposure and one measurement row; rows are not virtual detector bins.

The physical geometry has a single GAGG crystal and homogeneous-Air support volumes. A fixed-axis 2×2 mm square crystal, isotropic point source, and uniform air permit expected-response reuse under lateral sign flips and x/y swaps (D4 symmetry). Calibration directly simulates every unique relative XY offset in the grid difference set: {{(|dx|,|dy|): 0 ≤ |dy| ≤ |dx| ≤ 30 mm}}, 28 conditions. No response outside this measured offset grid is extrapolated. The symmetry mapping is recorded per matrix element. Reuse is valid only while material, source, detector orientation, energy, digitizer, and physics remain unchanged.

Calibration uses a 3.7 MBq point source for 10 s per unique offset; the independent phantom uses the same total activity and 10 s per physical pose. Task counts are {calibration_tasks} calibration conditions and {phantom_tasks} phantom exposures, for 77 Gate invocations and a planning estimate of {histories:,} emitted histories. The baseline yielded 233 Singles per 3.7 million emitted histories, so a 10 s central calibration would be about 2,330 Singles if its response repeats; this is planning extrapolation, not a new measurement. Baseline logs contain no reliable elapsed-time measurement, so no wall-time claim is made. Slurm workers request one CPU and 8 GB each, four workers maximum (32 GB aggregate), and 24 hours per worker allocation.

Image coordinates map directly to Gate x/y in millimetres; sources lie at z = -51 mm. Detector pose coordinates translate the Gate cylindricalPET parent and all daughters at z = 0, with no rotation. The response is measured at source-minus-detector relative positions.

## System-matrix contract

Matrix rows i are physical detector-pose exposures in runtime/manifests/measurement_row_map.csv; columns j are image voxels/source points in runtime/manifests/image_voxel_map.csv ordered row-major by y then x. The measured calibration count is nᵢⱼ. Its response estimate is Rᵢⱼ = nᵢⱼ/(a·tcal), in cps/Bq. The expected-count operator is Hᵢⱼ = Rᵢⱼ·Tᵢ, in expected counts/Bq for phantom exposure at row i. The 49×49 matrix is assembled by the explicit measured relative-offset map. raw_counts_symmetry_expanded.npy records observed counts reused under exact symmetry; it does not claim independent event counts for every element. Unique task ROOT files and count metadata remain available for audit.

## Sensitivity, response masks, FWHM

Sensitivity maps use the configured absolute system sensitivity Sⱼ = sumᵢRᵢⱼ in cps/Bq and cps/MBq. The time-weighted mean sensitivity for a sequential scan, sumᵢ(TᵢRᵢⱼ)/sumᵢTᵢ, and integrated scan counts/Bq are retained as separately labeled quantities. Per-pose masks threshold measured response at the configured fraction of the row peak. Axis profiles through each response maximum use linearly interpolated half-maximum crossings; widths without both crossings inside the calibrated FOV are invalid and retain reasons. Runtime FWHM is not available before Gate runs.

## ASCI and JI applicability

Reference ASCI counts occupied angular bins of valid beam masks over each image pixel. OneCube's translated bare uncollimated crystal has no beam-direction encoding; pose-position azimuth is not a projection angle. Beam-based ASCI is configured as NOT PHYSICALLY APPLICABLE, and no ASCI heatmap or fabricated angular occupancy is emitted. A separate pose-design plot shows translations only. JI follows (mean_sensitivity_cps_per_bq / mean_fwhm_mm²) × (ASCI_percent/100) and remains null unless all three inputs are physically defined and measured.

## Phantom and independent Gate data

The phantom is a 7×7 voxel-grid object with four independently weighted Gaussian hot spots and a low positive background, normalized once to 3.7 MBq total. Each voxel is represented by an isotropic 140 keV point source whose activity equals that voxel's Bq value. Every detector pose receives a separate Gate phantom acquisition with the complete source distribution. Those Singles counts are the primary measured data vector. Model-based expected and seeded Poisson projections are comparison data and are not independent Gate validation.

## Forward projection and MLEM

Forward projection uses y_expected = H @ x_true; a seeded synthetic comparison is Poisson sampled. MLEM consumes generic H[measurement,voxel] and y[measurement] arrays, uses H.T @ ones sensitivity, positive uniform initialization over observable voxels, nonnegative updates, explicit epsilon stabilization, and saves every configured iterate, relative update, and Poisson log likelihood. Filtering is disabled. Synthetic-Poisson and independent-Gate reconstructions are evaluated separately.

## Runtime results

<!-- RUNTIME_RESULTS_START -->
Not run. No Gate process, Slurm submission, calibration, phantom acquisition, matrix assembly from new Monte Carlo counts, or scientific reconstruction has been executed during preparation. The runtime finalizer replaces this section with actual task provenance, matrix diagnostics, metrics, validation, and figure links.
<!-- RUNTIME_RESULTS_END -->

## Scientific limits

The bare single crystal is uncollimated and its axial source response is broad. Translation produces independent physical measurements but may yield a strongly correlated, poorly conditioned response matrix; measured singular values and reconstruction errors determine what can be claimed. FWHM can be undefined if the sampled FOV does not cross half maximum. ASCI and JI are not expected to be defined for this response. The inherited OneCube physics macro is preserved; this experiment does not silently upgrade or claim validation of omitted interaction processes.

## MagicCubeFinal transfer

Generic matrix input, absolute response normalization, sensitivity, PPDF, threshold masks, interpolated FWHM, physically gated ASCI/JI, phantom vectors, projection, MLEM, metrics, diagnostics, and plotting consume arrays and explicit row/voxel maps. MagicCubeFinal can reuse these modules with its own detector map, acquisition map, voxel grid, event reducer, and response matrix. The OneCube GATE macro generator and D4 symmetry reducer are system-specific and require a separate physical proof before reuse.

## Preparation validation and launch

Static preparation checks deterministic ordering, 28 relative-offset tasks, 49 independent measurement rows, 49 voxel columns, macro isolation/output paths, phantom activity normalization, and shard configuration. Runtime validation additionally requires all GATE tasks, ROOT Singles counts, matrix products, reconstructions, plots, and provenance. Scientific acceptance is deferred to measured outputs.

Manual production command:

{launch_fence}bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCubeImagingFinal/slurm"
bash par_imaging_full.sh
{launch_fence}
"""


def prepare() -> dict:
    config = load_config(PROJECT_ROOT)
    baseline = (PROJECT_ROOT / config["baseline_project_relative"]).resolve()
    if not baseline.is_dir():
        raise FileNotFoundError(f"Frozen validated OneCube project is missing: {baseline}")
    required_assets = [baseline / config["baseline"]["material_database"]]
    required_assets.extend(baseline / path for path in config["baseline"]["geometry_macros"])
    required_assets.extend([
        baseline / "GATE-Macro" / "source.mac",
        baseline / "GATE-Macro" / "output.mac",
    ])
    missing = [str(path) for path in required_assets if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required frozen OneCube assets are missing: " + ", ".join(missing))

    voxels = make_voxels(config)
    poses = make_poses(config)
    phantom_image, phantom_vector, phantom_metadata = make_phantom(config, voxels)
    phantom_activity = source_rows(
        phantom_vector, voxels, float(config["phantom"]["total_activity_Bq"])
    )
    offset_rows = []
    max_offset = int(config["acquisition"]["max_relative_offset_index"])
    pitch = float(config["image"]["voxel_pitch_mm"])
    for task_id, (dx_index, dy_index) in enumerate(d4_representatives(max_offset)):
        offset_rows.append({
            "task_id": task_id,
            "condition_id": f"offset_{dx_index}_{dy_index}",
            "offset_dx_index": dx_index,
            "offset_dy_index": dy_index,
            "source_x_mm": dx_index * pitch,
            "source_y_mm": dy_index * pitch,
            "source_z_mm": float(config["image"]["plane_z_mm"]),
            "detector_id": int(config["baseline"]["detector_id"]),
            "detector_x_mm": 0.0,
            "detector_y_mm": 0.0,
            "detector_z_mm": float(config["acquisition"]["detector_z_mm"]),
            "activity_Bq": float(config["acquisition"]["calibration_activity_Bq"]),
            "acquisition_s": float(config["acquisition"]["calibration_exposure_s"]),
            "seed": int(config["acquisition"]["seed_base_calibration"]) + task_id,
            "source_energy_keV": float(config["baseline"]["source_energy_keV"]),
            "macro_path": f"runtime/generated_macros/calibration/task_{task_id:03d}.mac",
            "root_base_path": f"runtime/calibration/root/task_{task_id:03d}.root",
            "singles_root_path": f"runtime/calibration/root/task_{task_id:03d}.Singles.root",
            "hits_root_path": f"runtime/calibration/root/task_{task_id:03d}.hits.root",
        })
    for pose in poses:
        pose["exposure_s"] = float(config["acquisition"]["phantom_exposure_s"])
    phantom_rows = []
    for pose in poses:
        pose_id = int(pose["pose_id"])
        phantom_rows.append({
            **pose,
            "task_id": pose_id,
            "seed": int(config["acquisition"]["seed_base_phantom"]) + pose_id,
            "activity_total_Bq": float(config["phantom"]["total_activity_Bq"]),
            "acquisition_s": float(config["acquisition"]["phantom_exposure_s"]),
            "macro_path": f"runtime/generated_macros/phantom/pose_{pose_id:03d}.mac",
            "root_base_path": f"runtime/phantom/root/pose_{pose_id:03d}.root",
            "singles_root_path": f"runtime/phantom/root/pose_{pose_id:03d}.Singles.root",
            "hits_root_path": f"runtime/phantom/root/pose_{pose_id:03d}.hits.root",
        })

    runtime = PROJECT_ROOT / "runtime"
    results = PROJECT_ROOT / "results"
    directories = (
        runtime / "manifests", runtime / "generated_macros" / "calibration",
        runtime / "generated_macros" / "phantom", runtime / "calibration" / "root",
        runtime / "calibration" / "completions", runtime / "phantom" / "root",
        runtime / "phantom" / "completions", runtime / "reduced",
        runtime / "provenance", runtime / "logs", runtime / "quarantine",
        results / "system_matrix", results / "sensitivity", results / "response",
        results / "fwhm", results / "asci", results / "phantom", results / "projections",
        results / "reconstruction", results / "plots", results / "validation",
    )
    for path in directories:
        path.mkdir(parents=True, exist_ok=True)

    write_csv(runtime / "manifests" / "image_voxel_map.csv", voxels, [
        "voxel_id", "source_id", "x_index", "y_index", "x_mm", "y_mm", "z_mm",
    ])
    write_csv(runtime / "manifests" / "acquisition_poses.csv", poses, [
        "pose_id", "row_id", "pose_x_index", "pose_y_index", "detector_id",
        "detector_x_mm", "detector_y_mm", "detector_z_mm", "rotation_x_deg",
        "rotation_y_deg", "rotation_z_deg", "pose_kind", "exposure_s",
    ])
    write_csv(runtime / "manifests" / "response_simulation_manifest.csv", offset_rows, [
        "task_id", "condition_id", "offset_dx_index", "offset_dy_index",
        "source_x_mm", "source_y_mm", "source_z_mm", "detector_id",
        "detector_x_mm", "detector_y_mm", "detector_z_mm", "activity_Bq",
        "acquisition_s", "seed", "source_energy_keV", "macro_path",
        "root_base_path", "singles_root_path", "hits_root_path",
    ])
    write_csv(runtime / "manifests" / "measurement_row_map.csv", [
        {**pose, "measurement_type": "one independent physical detector-pose exposure"}
        for pose in poses
    ], [
        "row_id", "pose_id", "pose_x_index", "pose_y_index", "detector_id",
        "detector_x_mm", "detector_y_mm", "detector_z_mm", "rotation_x_deg",
        "rotation_y_deg", "rotation_z_deg", "exposure_s", "measurement_type",
    ])
    write_csv(runtime / "manifests" / "phantom_acquisition_manifest.csv", phantom_rows, [
        "task_id", "pose_id", "row_id", "detector_id", "detector_x_mm",
        "detector_y_mm", "detector_z_mm", "rotation_x_deg", "rotation_y_deg",
        "rotation_z_deg", "seed", "activity_total_Bq", "acquisition_s",
        "macro_path", "root_base_path", "singles_root_path", "hits_root_path",
    ])
    write_csv(runtime / "manifests" / "phantom_voxel_sources.csv", phantom_activity, [
        "voxel_id", "source_id", "x_index", "y_index", "x_mm", "y_mm", "z_mm", "activity_Bq",
    ])
    save_npy(results / "phantom" / "phantom_activity_bq.npy", phantom_vector)
    save_npy(results / "phantom" / "phantom_image_bq.npy", phantom_image)
    write_csv(results / "phantom" / "phantom_voxel_activity.csv", phantom_activity, [
        "voxel_id", "source_id", "x_index", "y_index", "x_mm", "y_mm", "z_mm", "activity_Bq",
    ])
    write_json(results / "phantom" / "phantom_metadata.json", {
        **{key: value for key, value in phantom_metadata.items() if key != "hot_mask"},
        "activity_units": "Bq per voxel",
        "voxel_ordering": config["image"]["voxel_order"],
        "hot_mask": phantom_metadata["hot_mask"],
    })

    for task in offset_rows:
        source = {
            "x_mm": task["source_x_mm"], "y_mm": task["source_y_mm"],
            "z_mm": task["source_z_mm"], "activity_Bq": task["activity_Bq"],
        }
        _write_macro(
            PROJECT_ROOT / task["macro_path"], config, baseline, 0.0, 0.0,
            int(task["seed"]), PROJECT_ROOT / task["root_base_path"], [source],
            float(task["acquisition_s"]),
        )
    for task in phantom_rows:
        _write_macro(
            PROJECT_ROOT / task["macro_path"], config, baseline,
            float(task["detector_x_mm"]), float(task["detector_y_mm"]),
            int(task["seed"]), PROJECT_ROOT / task["root_base_path"],
            phantom_activity, float(task["acquisition_s"]),
        )

    effective_config = {
        "config": config,
        "config_sha256": file_sha256(PROJECT_ROOT / "config" / "imaging_config.json"),
        "baseline_project": str(baseline),
        "baseline_macro_sha256": {
            str(path.relative_to(baseline)): file_sha256(path) for path in required_assets
        },
        "calibration_task_count": len(offset_rows),
        "physical_phantom_measurement_count": len(phantom_rows),
        "image_voxel_count": len(voxels),
        "matrix_expected_shape": [len(poses), len(voxels)],
        "phantom_metadata": {key: value for key, value in phantom_metadata.items() if key != "hot_mask"},
        "runtime_executed": False,
    }
    write_json(runtime / "provenance" / "preparation_manifest.json", effective_config)
    plot_paths = render_preparation(PROJECT_ROOT, config, voxels, poses, phantom_image, phantom_metadata)
    write_json(runtime / "provenance" / "preparation_figures.json", {"figures": plot_paths})
    report_path = PROJECT_ROOT / config["outputs"]["primary_report"]
    if not report_path.exists():
        report_path.write_text(
            _report_text(
                config, len(offset_rows), len(phantom_rows),
                int(config["resources"]["estimated_primary_histories"]),
            ),
            encoding="utf-8",
        )
    return {
        "project_root": str(PROJECT_ROOT),
        "calibration_tasks": len(offset_rows),
        "phantom_measurement_tasks": len(phantom_rows),
        "image_voxels": len(voxels),
        "expected_matrix_shape": [len(poses), len(voxels)],
        "phantom_activity_Bq": float(phantom_vector.sum()),
        "runtime_executed": False,
        "preparation_figures": plot_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare deterministic OneCube full-imaging manifests and Gate macros.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare()
    except Exception as error:
        print(f"Preparation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2) if args.json else "OneCube imaging experiment manifests and macros prepared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
