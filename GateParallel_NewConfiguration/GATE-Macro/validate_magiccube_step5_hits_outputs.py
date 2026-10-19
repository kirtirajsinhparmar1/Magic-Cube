#!/usr/bin/env python3
"""Validate the two bounded Step-5 raw-Hits diagnostic runs."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any


FATAL_PATTERNS = (
    re.compile(r"fatal exception", re.IGNORECASE),
    re.compile(r"command not found", re.IGNORECASE),
    re.compile(r"failed to get the system corresponding to that digitizer", re.IGNORECASE),
    re.compile(r"\bg4exception\b.*\babort\b", re.IGNORECASE),
    re.compile(r"\babort\b", re.IGNORECASE),
)


def read_exit_code(path: Path, override: int | None) -> int | None:
    if override is not None:
        return override
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def discover_hits_files(output_dir: Path, label: str) -> list[Path]:
    token = f"magiccube_step5_hits_{label}".lower()
    return sorted(
        path
        for path in output_dir.glob("*.root")
        if token in path.name.lower() and "hit" in path.name.lower()
    )


def read_log(output_dir: Path, label: str) -> tuple[Path | None, str]:
    path = output_dir / f"{label}_gate.log"
    if not path.is_file():
        return None, ""
    try:
        return path, path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return path, ""


def fatal_log_matches(log_text: str) -> list[str]:
    matches: list[str] = []
    for line in log_text.splitlines():
        if any(pattern.search(line) for pattern in FATAL_PATTERNS):
            matches.append(line.strip())
    return matches


def inspect_root(path: Path, uproot: Any) -> tuple[list[tuple[str, int, Any]], str | None]:
    trees: list[tuple[str, int, Any]] = []
    try:
        with uproot.open(path) as root_file:
            for key, class_name in root_file.classnames(recursive=True).items():
                if not str(class_name).startswith("TTree"):
                    continue
                tree_name = str(key).split(";", 1)[0]
                tree = root_file[tree_name]
                trees.append((tree_name, int(tree.num_entries), tree))
    except Exception as exc:  # noqa: BLE001 - report the file-level check failure
        return [], f"{type(exc).__name__}: {exc}"
    return trees, None


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def choose_branch(branches: list[str], candidates: set[str]) -> str | None:
    by_normalized = {normalized(branch): branch for branch in branches}
    for candidate in candidates:
        if candidate in by_normalized:
            return by_normalized[candidate]
    return None


def load_detector_centers() -> list[tuple[float, float, float]]:
    map_path = Path(__file__).resolve().parent / "detector_map.csv"
    centers: list[tuple[float, float, float]] = []
    with map_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        normalized_fields = {normalized(field): field for field in fields}

        def field(*names: str) -> str:
            for name in names:
                if name in normalized_fields:
                    return normalized_fields[name]
            raise KeyError(names)

        x_field = field("globalxmm", "globalx", "xmm")
        y_field = field("globalymm", "globaly", "ymm")
        z_field = field("globalzmm", "globalz", "zmm")
        for row in reader:
            centers.append((float(row[x_field]), float(row[y_field]), float(row[z_field])))
    return centers


def check_position_mapping(trees: list[tuple[str, int, Any]]) -> None:
    """Perform the optional position-derived check when suitable branches exist."""
    try:
        centers = load_detector_centers()
    except Exception as exc:  # noqa: BLE001 - this is an optional check
        print(f"POSITION-DERIVED MAPPING: NOT PERFORMED — {type(exc).__name__}: {exc}")
        return

    x_candidates = {"globalposx", "globalpositionx", "globalx", "globalxmm"}
    y_candidates = {"globalposy", "globalpositiony", "globaly", "globalymm"}
    z_candidates = {"globalposz", "globalpositionz", "globalz", "globalzmm"}
    mapped = 0
    unmapped = 0
    ambiguous = 0
    arrays_found = False

    for tree_name, _, tree in trees:
        branches = [str(name).split(";", 1)[0] for name in tree.keys()]
        x_name = choose_branch(branches, x_candidates)
        y_name = choose_branch(branches, y_candidates)
        z_name = choose_branch(branches, z_candidates)
        if not (x_name and y_name and z_name):
            continue
        arrays_found = True
        try:
            x_values = tree[x_name].array(library="np")
            y_values = tree[y_name].array(library="np")
            z_values = tree[z_name].array(library="np")
            for x_value, y_value, z_value in zip(x_values, y_values, z_values):
                point = (float(x_value), float(y_value), float(z_value))
                matches = sum(
                    abs(point[0] - center[0]) <= 1.01
                    and abs(point[1] - center[1]) <= 1.01
                    and abs(point[2] - center[2]) <= 1.01
                    for center in centers
                )
                if matches == 1:
                    mapped += 1
                elif matches == 0:
                    unmapped += 1
                else:
                    ambiguous += 1
        except Exception as exc:  # noqa: BLE001 - optional branch-level check
            print(
                "POSITION-DERIVED MAPPING: NOT PERFORMED — "
                f"{tree_name}: {type(exc).__name__}: {exc}"
            )
            return

    if not arrays_found:
        print("POSITION-DERIVED MAPPING: NOT PERFORMED — position branches unavailable")
    else:
        print(
            "POSITION-DERIVED MAPPING: "
            f"mapped={mapped} unmapped={unmapped} ambiguous={ambiguous}"
        )


def validate_test(
    label: str,
    output_dir: Path,
    exit_code: int | None,
    uproot: Any | None,
) -> tuple[bool, bool]:
    print(f"\n{label.upper()} TEST")
    print(f"Gate exit code: {exit_code if exit_code is not None else 'MISSING'}")
    log_path, log_text = read_log(output_dir, label)
    if log_path is None:
        print("GATE log: MISSING")
        fatal_lines: list[str] = []
    else:
        print(f"GATE log: {log_path.name}")
        fatal_lines = fatal_log_matches(log_text)
        if fatal_lines:
            print("Fatal/error matches:")
            for line in fatal_lines[:10]:
                print(f"  {line}")

    root_files = discover_hits_files(output_dir, label)
    print("Hits files:")
    if root_files:
        for path in root_files:
            print(f"  {path.name}")
    else:
        print("  NONE")

    if uproot is None:
        print("ROOT CONTENT CHECK: NOT PERFORMED — VALIDATOR ENVIRONMENT ERROR")
        print("Status: VALIDATOR_ENVIRONMENT_ERROR")
        return False, True

    all_trees: list[tuple[str, int, Any]] = []
    readable = True
    total_entries = 0
    for path in root_files:
        trees, error = inspect_root(path, uproot)
        if error is not None:
            readable = False
            print(f"  ROOT READ ERROR {path.name}: {error}")
            continue
        for tree_name, entries, tree in trees:
            print(f"  {path.name} :: {tree_name} entries={entries}")
            all_trees.append((tree_name, entries, tree))
            total_entries += entries

    print(f"Total Hits entries: {total_entries}")
    if label == "internal" and all_trees and total_entries > 0:
        check_position_mapping(all_trees)

    passed = (
        exit_code == 0
        and log_path is not None
        and not fatal_lines
        and bool(root_files)
        and readable
        and bool(all_trees)
        and total_entries > 0
    )
    print(f"Status: {'PASS' if passed else 'FAIL'}")
    return passed, False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--internal-exit-code", type=int)
    parser.add_argument("--external-exit-code", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    try:
        import uproot  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - distinguish validator environment failure
        uproot = None
        print(f"ROOT validator import: {type(exc).__name__}: {exc}")

    internal_code = read_exit_code(
        output_dir / "internal_gate_exit_code.txt", args.internal_exit_code
    )
    external_code = read_exit_code(
        output_dir / "external_gate_exit_code.txt", args.external_exit_code
    )
    internal_pass, internal_env_error = validate_test(
        "internal", output_dir, internal_code, uproot
    )
    external_pass, external_env_error = validate_test(
        "external", output_dir, external_code, uproot
    )

    if internal_env_error or external_env_error:
        interpretation = "VALIDATION_INCOMPLETE_ENVIRONMENT_ERROR"
        result_code = 2
    elif internal_pass and external_pass:
        interpretation = "RAW_HITS_PATH_VALIDATED"
        result_code = 0
    elif internal_pass and not external_pass:
        interpretation = "INTERNAL_PASS_EXTERNAL_FAIL"
        result_code = 1
    elif not internal_pass and external_pass:
        interpretation = "DIAGNOSTIC_INCONSISTENCY"
        result_code = 1
    else:
        interpretation = "PRODUCTION_SD_NOT_PRODUCING_HITS"
        result_code = 1

    print(f"\nINTERPRETATION: {interpretation}")
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
