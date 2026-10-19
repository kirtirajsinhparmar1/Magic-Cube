#!/usr/bin/env python3
"""Authoritative post-runtime validator for the complete OneCube pipeline."""

import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from inspect_root import inspect_merged, load_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "onecube_config.json"
SIM_DIR = PROJECT_ROOT / "runtime" / "sim"
LOG_PATH = PROJECT_ROOT / "runtime" / "logs" / "gate.log"
RESULTS = PROJECT_ROOT / "results"
FINAL_PATH = RESULTS / "validation" / "final_validation.json"


def active_lines(path: Path) -> List[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def check_config(config: Dict[str, Any], failures: List[str]) -> None:
    detector = config["detector"]
    source = config["source"]
    acquisition = config["acquisition"]
    if detector["count"] != 1 or detector["detector_id"] != 0 or detector["material"] != "GAGG":
        failures.append("config detector contract is not one GAGG detector with ID 0")
    for axis in ("x", "y", "z"):
        if not math.isclose(float(detector[f"{axis}_mm"]), 0.0):
            failures.append(f"config detector {axis} center is not zero")
    for axis in ("x", "y", "z"):
        if not math.isclose(float(detector[f"size_{axis}_mm"]), 2.0):
            failures.append("config detector dimensions are not 2 x 2 x 2 mm")
            break
    if (
        source["source_count"] != 1
        or source["source_id"] != 0
        or source["particle"] != "gamma"
        or not math.isclose(float(source["energy_keV"]), 140.0)
        or not all(math.isclose(float(source[f"{axis}_mm"]), expected) for axis, expected in (("x", 0.0), ("y", 0.0), ("z", -51.0)))
        or source["position_type"] != "Point"
        or source["angular_type"] != "isotropic"
        or not math.isclose(float(source["activity_Bq"]), 3.7e6)
        or not math.isclose(float(source["surface_distance_mm"]), 50.0)
    ):
        failures.append("config source contract does not match the frozen OneCube source")
    if not (
        math.isclose(float(acquisition["start_s"]), 0.0)
        and math.isclose(float(acquisition["stop_s"]), 1.0)
        and math.isclose(float(acquisition["duration_s"]), 1.0)
        and math.isclose(float(acquisition["time_slice_s"]), 1.0)
    ):
        failures.append("config acquisition is not the frozen 0-to-1 second interval")


def check_gate_log(failures: List[str]) -> None:
    exit_path = SIM_DIR / "gate_exit_code.txt"
    if not exit_path.is_file():
        failures.append("Gate exit-code file is missing")
    else:
        try:
            if int(exit_path.read_text(encoding="utf-8").strip()) != 0:
                failures.append("Gate exit code is nonzero")
        except ValueError:
            failures.append("Gate exit-code file is not an integer")

    if not LOG_PATH.is_file():
        failures.append("Gate log is missing")
        return
    log_text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
    forbidden = [
        (re.compile(r"fatal exception", re.IGNORECASE), "Gate log contains Fatal Exception"),
        (re.compile(r"command not found", re.IGNORECASE), "Gate log contains COMMAND NOT FOUND"),
        (re.compile(r"corresponding-system", re.IGNORECASE), "Gate log contains a corresponding-system failure"),
        (re.compile(r"(?:gatespatialresolution.{0,120}fatal|fatal.{0,120}gatespatialresolution)", re.IGNORECASE), "Gate log contains a GateSpatialResolution fatal error"),
        (re.compile(r"(?:geometry.{0,120}(?:containment|overlap).{0,120}fatal|fatal.{0,120}(?:containment|overlap))", re.IGNORECASE), "Gate log contains a geometry containment/overlap fatal error"),
        (re.compile(r"\babort(?:ed)?\b", re.IGNORECASE), "Gate log contains abort"),
    ]
    for pattern, message in forbidden:
        if pattern.search(log_text):
            failures.append(message)


def root_file_check(failures: List[str]) -> Dict[str, Any]:
    raw = {}
    for kind in ("hits", "singles"):
        candidates = sorted(
            path
            for path in SIM_DIR.glob("*.root")
            if kind in path.name.lower()
        )
        if not candidates:
            failures.append(f"raw {kind} ROOT file is missing")
        elif any(path.stat().st_size <= 100 for path in candidates):
            failures.append(f"raw {kind} ROOT file is smaller than a minimal ROOT header")
        raw[kind] = [str(path) for path in candidates]
    return raw


def main() -> int:
    failures: List[str] = []
    try:
        config = load_config()
    except Exception as error:  # noqa: BLE001
        config = {}
        failures.append(f"config cannot be read: {error}")

    if config:
        check_config(config, failures)
    check_gate_log(failures)
    raw_files = root_file_check(failures)

    try:
        root_summary, root_failures = inspect_merged()
        failures.extend(root_failures)
    except Exception as error:  # noqa: BLE001
        root_summary = {}
        failures.append(f"merged ROOT inspection failed: {error}")

    if root_summary.get("hits_count", 0) <= 0:
        failures.append("merged Hits count is not positive")
    if root_summary.get("singles_count", 0) <= 0:
        failures.append("merged Singles count is not positive")
    if root_summary.get("canonical_detector_ids") != [0]:
        failures.append("canonical detector IDs are not exactly [0]")
    if root_summary.get("canonical_source_ids") != [0]:
        failures.append("canonical source IDs are not exactly [0]")

    ppdf_path = RESULTS / "ppdf" / "ppdf.parquet"
    try:
        ppdf = pd.read_parquet(ppdf_path)
        if len(ppdf) != 1:
            failures.append("PPDF does not contain exactly one row")
        else:
            row = ppdf.iloc[0]
            if int(row["detector_id"]) != 0 or int(row["source_id"]) != 0:
                failures.append("PPDF IDs are not detector 0 and source 0")
            if int(row["raw_singles_count"]) <= 0:
                failures.append("PPDF raw Singles count is not positive")
            if not math.isclose(float(row["ppdf"]), 1.0, rel_tol=0.0, abs_tol=1.0e-12):
                failures.append("PPDF normalized value is not 1.0")
    except Exception as error:  # noqa: BLE001
        failures.append(f"PPDF output is unreadable: {error}")

    matrix_path = RESULTS / "system_matrix" / "system_matrix.npy"
    try:
        matrix = np.load(matrix_path)
        if matrix.shape != (1, 1):
            failures.append(f"system matrix shape is {matrix.shape}, not (1, 1)")
        if not np.isfinite(matrix).all() or (matrix < 0).any():
            failures.append("system matrix contains a non-finite or negative response")
    except Exception as error:  # noqa: BLE001
        matrix = np.empty((0, 0))
        failures.append(f"system matrix .npy is unreadable: {error}")

    for required in (
        RESULTS / "system_matrix" / "system_matrix.parquet",
        RESULTS / "system_matrix" / "system_matrix.csv",
        RESULTS / "system_matrix" / "system_matrix_metadata.json",
    ):
        if not required.is_file() or required.stat().st_size == 0:
            failures.append(f"required system-matrix output is missing or empty: {required.name}")

    metadata_path = RESULTS / "system_matrix" / "system_matrix_metadata.json"
    if metadata_path.is_file():
        try:
            with metadata_path.open(encoding="utf-8") as stream:
                metadata = json.load(stream)
            if metadata.get("shape") != [1, 1] or metadata.get("npy_quantity") != "response_per_Bq_s":
                failures.append("system-matrix metadata does not document the 1x1 response representation")
            if metadata.get("raw_count_preserved") is not True:
                failures.append("system-matrix metadata does not preserve raw count")
        except Exception as error:  # noqa: BLE001
            failures.append(f"system-matrix metadata is unreadable: {error}")

    for plot_name in ("system_matrix_heatmap.png", "onecube_response_summary.png"):
        plot_path = RESULTS / "plots" / plot_name
        if not plot_path.is_file() or plot_path.stat().st_size == 0:
            failures.append(f"plot is missing or empty: {plot_name}")
        elif plot_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            failures.append(f"plot is not a PNG: {plot_name}")

    geometry_lines = active_lines(PROJECT_ROOT / "GATE-Macro" / "geometry.mac")
    plate_lines = active_lines(PROJECT_ROOT / "GATE-Macro" / "plate.mac")
    if any("K9" in line or "k9" in line for line in geometry_lines):
        failures.append("geometry contains K9")
    if any("tungsten" in line.lower() or "MetalPlate" in line for line in geometry_lines + plate_lines):
        failures.append("geometry contains a mechanical collimator")
    if any("repeaters" in line or "cubicArray" in line for line in geometry_lines):
        failures.append("geometry contains a repeater")
    if plate_lines:
        failures.append("plate compatibility macro contains active geometry")

    FINAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    classification = "ONECUBE_END_TO_END_PASS" if not failures else "ONECUBE_END_TO_END_FAIL"
    result = {
        "classification": classification,
        "failures": failures,
        "raw_files": raw_files,
        "root_summary": root_summary,
        "matrix_shape": list(matrix.shape),
        "config_path": str(CONFIG_PATH),
    }
    with FINAL_PATH.open("w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")

    if failures:
        for failure in failures:
            print(f"FAILED: {failure}")
    print(classification)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
