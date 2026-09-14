#!/usr/bin/env python3
"""Bounded post-run checks for the Step-5 production-system candidate."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAP_PATH = ROOT / "detector_map.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--gate-exit-code", required=True, type=int)
    return parser.parse_args()


def log_path(output_dir: Path) -> Path | None:
    preferred = output_dir / "magiccube_step5_system_gate.log"
    if preferred.is_file():
        return preferred
    logs = sorted(output_dir.glob("*.log"))
    return logs[0] if logs else None


def load_detector_positions() -> list[tuple[float, float, float, int]] | None:
    if not MAP_PATH.is_file():
        return None
    try:
        with MAP_PATH.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return None
    if not rows:
        return None

    normalized = {key.strip().lower().replace("-", "_"): key for key in rows[0]}
    id_key = normalized.get("detector_id")
    axis_keys: dict[str, str] = {}
    aliases = {
        "x": ("x_mm", "center_x_mm", "centre_x_mm", "global_x_mm", "position_x_mm"),
        "y": ("y_mm", "center_y_mm", "centre_y_mm", "global_y_mm", "position_y_mm"),
        "z": ("z_mm", "center_z_mm", "centre_z_mm", "global_z_mm", "position_z_mm"),
    }
    for axis, names in aliases.items():
        for name in names:
            if name in normalized:
                axis_keys[axis] = normalized[name]
                break
    if id_key is None or len(axis_keys) != 3:
        return None

    positions: list[tuple[float, float, float, int]] = []
    try:
        for row in rows:
            positions.append(
                (
                    float(row[axis_keys["x"]]),
                    float(row[axis_keys["y"]]),
                    float(row[axis_keys["z"]]),
                    int(row[id_key]),
                )
            )
    except (KeyError, TypeError, ValueError):
        return None
    return positions


def branch_name_for_axis(names: list[str], axis: str) -> str | None:
    for name in names:
        normalized = re.sub(r"[^a-z0-9]", "", name.lower())
        if "globalpos" + axis in normalized:
            return name
    return None


def check_positions(tree, names: list[str], positions) -> tuple[bool, str]:
    axes = {axis: branch_name_for_axis(names, axis) for axis in "xyz"}
    if any(value is None for value in axes.values()):
        return True, "POSITION MAPPING CHECK: NOT PERFORMED — no complete global position branch set"
    if positions is None:
        return False, "POSITION MAPPING CHECK: NOT PERFORMED — detector-map coordinate columns unavailable"

    try:
        arrays = tree.arrays(
            [axes["x"], axes["y"], axes["z"]],
            entry_start=0,
            entry_stop=10000,
            library="np",
        )
        values = zip(arrays[axes["x"]], arrays[axes["y"]], arrays[axes["z"]])
    except Exception as exc:
        return False, f"POSITION MAPPING CHECK: NOT PERFORMED — {exc}"

    checked = 0
    for x_value, y_value, z_value in values:
        try:
            x = float(x_value)
            y = float(y_value)
            z = float(z_value)
        except (TypeError, ValueError):
            return False, "POSITION MAPPING CHECK: FAIL — non-numeric position branch"
        if not all(math.isfinite(value) for value in (x, y, z)):
            return False, "POSITION MAPPING CHECK: FAIL — non-finite position"

        distances = sorted(
            (
                (x - map_x) ** 2 + (y - map_y) ** 2 + (z - map_z) ** 2,
                detector_id,
            )
            for map_x, map_y, map_z, detector_id in positions
        )
        if not distances or distances[0][0] >= 2.1**2:
            return False, "POSITION MAPPING CHECK: FAIL — position is outside an unambiguous detector center"
        if len(distances) > 1 and math.isclose(
            distances[0][0],
            distances[1][0],
            rel_tol=0.0,
            abs_tol=1.0e-8,
        ):
            return False, "POSITION MAPPING CHECK: FAIL — nearest detector mapping is ambiguous"
        checked += 1

    return True, f"POSITION MAPPING CHECK: PASS — {checked} global positions mapped unambiguously"


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    failures: list[str] = []

    if args.gate_exit_code != 0:
        failures.append(f"Gate exit code is {args.gate_exit_code}, expected 0")

    gate_log = log_path(output_dir)
    gate_text = ""
    if gate_log is None:
        failures.append("no GATE log was found")
    else:
        gate_text = gate_log.read_text(encoding="utf-8", errors="replace")
        if "Fatal Exception" in gate_text:
            failures.append("GATE log contains Fatal Exception")
        if "COMMAND NOT FOUND" in gate_text:
            failures.append("GATE log contains COMMAND NOT FOUND")
        if "Failed to get the system corresponding to that digitizer" in gate_text:
            failures.append("GateSpatialResolution system lookup failure remains")
        if "G4Exception" in gate_text and "Abort" in gate_text:
            failures.append("GATE log contains an aborting G4Exception")

    root_files = sorted(path for path in output_dir.glob("*.root") if path.is_file())
    if not root_files:
        failures.append("no ROOT output files were found")
    elif any(path.stat().st_size == 0 for path in root_files):
        failures.append("a ROOT output file is empty")

    if failures:
        print("STEP-5 SYSTEM OUTPUT VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    try:
        import uproot
    except Exception as exc:
        print("ROOT CONTENT CHECK: NOT PERFORMED — VALIDATOR ENVIRONMENT ERROR")
        print(f"- {exc}")
        print("STEP-5 SYSTEM OUTPUT VALIDATION: INCOMPLETE")
        return 2

    hit_entries = 0
    single_entries = 0
    position_checks: list[str] = []
    positions = load_detector_positions()
    try:
        for path in root_files:
            with uproot.open(path) as root_file:
                for key in root_file.keys(recursive=True):
                    key_text = key.decode() if isinstance(key, bytes) else str(key)
                    object_name = key_text.split(";")[0]
                    try:
                        tree = root_file[object_name]
                    except Exception:
                        continue
                    if not hasattr(tree, "num_entries"):
                        continue
                    entries = int(tree.num_entries)
                    lower = object_name.lower()
                    is_hits = "hit" in lower
                    is_singles = "single" in lower
                    if is_hits:
                        hit_entries += entries
                    if is_singles:
                        single_entries += entries
                    if is_hits or is_singles:
                        names = [
                            name.decode() if isinstance(name, bytes) else str(name)
                            for name in tree.keys()
                        ]
                        ok, message = check_positions(tree, names, positions)
                        position_checks.append(message)
                        if not ok:
                            failures.append(message)
    except Exception as exc:
        print("ROOT CONTENT CHECK: NOT PERFORMED — VALIDATOR ENVIRONMENT ERROR")
        print(f"- {exc}")
        print("STEP-5 SYSTEM OUTPUT VALIDATION: INCOMPLETE")
        return 2

    if hit_entries <= 0:
        failures.append("no non-empty Hits tree was found")
    if single_entries <= 0:
        failures.append("no non-empty Singles tree was found")

    print(f"Hits entries: {hit_entries}")
    print(f"Singles entries: {single_entries}")
    for message in position_checks:
        print(message)

    if failures:
        print("STEP-5 SYSTEM OUTPUT VALIDATION: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("ROOT CONTENT CHECK: PASS")
    print("STEP-5 SYSTEM OUTPUT VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
