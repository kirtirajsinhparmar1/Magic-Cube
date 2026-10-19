#!/usr/bin/env python3
"""Validate generated OneCube visualization artifacts without running simulation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from visualization_common import (
    VisualizationError,
    load_configs,
    output_dir,
    read_csv_rows,
    runtime_dir,
    write_json,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def valid_png(path: Path) -> bool:
    if not nonempty(path):
        return False
    with path.open("rb") as handle:
        return handle.read(8) == PNG_SIGNATURE


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise VisualizationError(f"missing JSON summary: {path}")
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    parser.add_argument("--require-report", action="store_true",
                        help="also require the final markdown report")
    args = parser.parse_args()
    failures: list[str] = []
    checks: dict[str, bool] = {}
    try:
        visual, source, source_path = load_configs(args.config)
        out = output_dir(visual, args.config)
        runtime = runtime_dir(visual, args.config)
        required_pngs = list(visual["required_pngs"])
        for name in required_pngs:
            path = out / name
            passed = valid_png(path)
            checks[f"PNG:{name}"] = passed
            if not passed:
                failures.append(f"missing, empty, or invalid PNG: {path}")

        inspection = load_json(runtime / "root_inspection.json")
        for kind in ("hits", "singles"):
            count = int(inspection[kind]["entry_count"])
            passed = count > 0
            checks[f"ROOT:{kind}_entries"] = passed
            if not passed:
                failures.append(f"{kind} ROOT entry count is not positive: {count}")
        if inspection["hits"]["positions"]["within_detector"] is not True:
            failures.append("Hits positions are not verified inside the configured cube")
        if inspection["hits"]["identity"]["canonical_detector_ids"] != [0] * inspection["hits"]["entry_count"]:
            failures.append("Hits canonical detector identity is not exclusively detector 0")

        intensity = load_json(runtime / "cube_intensity_summary.json")
        if int(intensity["hits_in_cube"]) <= 0 or float(intensity["total_weight"]) <= 0:
            failures.append("cube intensity summary has no positive in-cube response")
        if len(intensity["bin_shape"]) != 3:
            failures.append("cube intensity summary is not 3D")

        time_energy = load_json(runtime / "time_energy_availability.json")
        for name, item in time_energy["plots"].items():
            if item["available"]:
                path = out / item["output"]
                if not valid_png(path):
                    failures.append(f"available {name} summary missing or invalid: {path}")
            elif not item.get("reason"):
                failures.append(f"unavailable {name} summary lacks an explicit reason")

        singles = load_json(runtime / "singles_availability.json")
        if not singles["positions"].get("reason"):
            failures.append("Singles position availability lacks an explicit statement")
        if singles["positions"]["available"]:
            position_path = singles["positions"].get("output")
            if not position_path or not valid_png(out / position_path):
                failures.append("Singles position data is available but its PNG is missing")

        animation = load_json(runtime / "animation_status.json")
        if animation.get("supported"):
            animation_path = Path(animation.get("output", ""))
            if not nonempty(animation_path):
                failures.append(f"animation marked supported but output is missing: {animation_path}")
        elif not animation.get("reason"):
            failures.append("animation marked unavailable without a concrete reason")

        project_root = source_path.parents[1]
        ppdf_rows = read_csv_rows(project_root / "results" / "ppdf" / "ppdf.csv")
        matrix_rows = read_csv_rows(project_root / "results" / "system_matrix" / "system_matrix.csv")
        if len(ppdf_rows) != 1 or abs(float(ppdf_rows[0]["ppdf"]) - 1.0) > 1e-6:
            failures.append("PPDF product is not exactly one row with ppdf approximately 1")
        if len(matrix_rows) != 1 or int(float(matrix_rows[0]["raw_singles_count"])) <= 0:
            failures.append("system-matrix product lacks a positive raw Singles count")
        matrix_path = project_root / "results" / "system_matrix" / "system_matrix.npy"
        matrix = np.load(matrix_path, allow_pickle=False)
        if matrix.shape != (1, 1) or not np.isfinite(matrix[0, 0]) or matrix[0, 0] < 0:
            failures.append(f"system matrix is not finite/nonnegative shape (1,1): {matrix.shape}")

        report = out / "VISUALIZATION_REPORT.md"
        if args.require_report and not nonempty(report):
            failures.append(f"final visualization report missing or empty: {report}")

    except (VisualizationError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    payload = {
        "status": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
        "report_required": bool(args.require_report),
    }
    try:
        visual, _, _ = load_configs(args.config)
        write_json(runtime_dir(visual, args.config) / "output_validation.json", payload)
    except Exception as exc:  # noqa: BLE001 - preserve the primary validation failure
        failures.append(f"could not write output validation JSON: {exc}")
        payload["status"] = "FAIL"
    if failures:
        print("ONECUBE VISUALIZATION OUTPUT VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ONECUBE VISUALIZATION OUTPUT VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
