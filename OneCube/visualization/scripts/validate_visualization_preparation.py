#!/usr/bin/env python3
"""Fast static validator for the isolated OneCube visualization package."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from visualization_common import DEFAULT_VIS_CONFIG, input_candidates, load_configs, output_dir, runtime_dir


SCRIPT_FILES = [
    "inspect_onecube_root.py",
    "plot_geometry_overview.py",
    "plot_detector_render.py",
    "plot_hits_3d.py",
    "plot_hits_projections.py",
    "plot_cube_intensity.py",
    "plot_time_energy_summaries.py",
    "plot_singles_summary.py",
    "plot_response_dashboard.py",
    "make_hit_animation.py",
    "validate_visualization_preparation.py",
    "validate_visualization_outputs.py",
    "final_visualization_summary.py",
    "visualization_common.py",
]
DOC_FILES = ["README.md", "VISUALIZATION_SPEC.md", "VISUALIZATION_RUNBOOK.md"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_VIS_CONFIG, help="visualization config JSON")
    args = parser.parse_args()
    failures: list[str] = []
    visual_root = args.config.resolve().parents[1]
    project_root = visual_root.parent

    for relative in DOC_FILES + [f"config/{args.config.name}"] + [f"scripts/{name}" for name in SCRIPT_FILES]:
        if not (visual_root / relative).is_file():
            failures.append(f"missing required file: {visual_root / relative}")
    for relative in ("outputs", "runtime"):
        if not (visual_root / relative).is_dir():
            failures.append(f"missing required directory: {visual_root / relative}")

    try:
        visual, source, source_path = load_configs(args.config)
    except Exception as exc:  # noqa: BLE001 - collect all preparation failures
        failures.append(f"configuration load failed: {exc}")
        visual = source = {}
        source_path = visual_root.parent / "config" / "onecube_config.json"

    if source:
        detector = source.get("detector", {})
        source_spec = source.get("source", {})
        acquisition = source.get("acquisition", {})
        checks = {
            "detector count": detector.get("count") == 1,
            "detector ID": detector.get("detector_id") == 0,
            "detector name": detector.get("name") == "onecube_crystal",
            "detector material": detector.get("material") == "GAGG",
            "detector center": all(float(detector.get(key, 999)) == 0 for key in ("x_mm", "y_mm", "z_mm")),
            "detector dimensions": all(float(detector.get(key, 999)) == 2 for key in ("size_x_mm", "size_y_mm", "size_z_mm")),
            "source count": source_spec.get("source_count") == 1,
            "source ID": source_spec.get("source_id") == 0,
            "source particle": source_spec.get("particle") == "gamma",
            "source energy": float(source_spec.get("energy_keV", -1)) == 140,
            "source position": all(float(source_spec.get(key, 999)) == expected for key, expected in (("x_mm", 0), ("y_mm", 0), ("z_mm", -51))),
            "source position type": source_spec.get("position_type") == "Point",
            "source surface distance": float(source_spec.get("surface_distance_mm", -1)) == 50,
            "source isotropic": source_spec.get("angular_type") == "isotropic",
            "source activity": float(source_spec.get("activity_Bq", -1)) == 3700000,
            "acquisition duration": float(acquisition.get("duration_s", -1)) == 1,
            "acquisition interval": float(acquisition.get("start_s", -1)) == 0 and float(acquisition.get("stop_s", -1)) == 1,
        }
        for label, passed in checks.items():
            if not passed:
                failures.append(f"OneCube scientific config mismatch: {label}")

    for kind in ("hits", "singles"):
        candidates = input_candidates(visual, kind, args.config) if visual else []
        if not any(path.is_file() and path.stat().st_size > 100 for path in candidates):
            failures.append(f"no non-empty {kind} ROOT input in configured candidates")
        for path in candidates:
            if path.is_absolute() and project_root not in path.parents:
                failures.append(f"{kind} candidate escapes OneCube project: {path}")

    for relative in (
        "results/ppdf/ppdf.csv",
        "results/system_matrix/system_matrix.csv",
        "results/system_matrix/system_matrix.npy",
    ):
        path = project_root / relative
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"existing OneCube data product missing or empty: {path}")

    required_modules = ("numpy", "pandas", "uproot", "matplotlib")
    for module_name in required_modules:
        if importlib.util.find_spec(module_name) is None:
            failures.append(f"required Python module unavailable: {module_name}")

    for script_name in SCRIPT_FILES:
        path = visual_root / "scripts" / script_name
        if path.is_file():
            try:
                compile(path.read_text(), str(path), "exec")
            except SyntaxError as exc:
                failures.append(f"Python syntax error in {path}: {exc}")

    # Keep static validation itself side-effect free with respect to generated figures.
    _ = output_dir, runtime_dir, source_path
    if failures:
        print("ONECUBE VISUALIZATION STATIC PREPARATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ONECUBE VISUALIZATION STATIC PREPARATION: PASS")
    print(f"package: {visual_root}")
    print("scientific source of truth: existing OneCube config and ROOT/results products")
    print("optional GATE visualization macro: not required; no bounded runtime added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
