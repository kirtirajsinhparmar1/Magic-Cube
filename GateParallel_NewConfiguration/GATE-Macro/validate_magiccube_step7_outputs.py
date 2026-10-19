#!/usr/bin/env python3
"""Validate one completed Step-7 run without assuming GATE branch names."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


POSITION_CANDIDATES = {
    "x": {
        "globalposx",
        "globalpositionx",
        "globalx",
        "globalxmm",
        "positionx",
        "posx",
        "localposx",
        "localpositionx",
    },
    "y": {
        "globalposy",
        "globalpositiony",
        "globaly",
        "globalymm",
        "positiony",
        "posy",
        "localposy",
        "localpositiony",
    },
    "z": {
        "globalposz",
        "globalpositionz",
        "globalz",
        "globalzmm",
        "positionz",
        "posz",
        "localposz",
        "localpositionz",
    },
}
VECTOR_POSITION_CANDIDATES = {
    "globalpos",
    "globalposition",
    "position",
    "pos",
    "localpos",
    "localposition",
}


@dataclass
class TreeRecord:
    path: Path
    tree_name: str
    kind: str
    tree: Any
    branches: list[str]
    types: dict[str, str]
    entries: int


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def choose_branch(branches: list[str], candidates: set[str]) -> str | None:
    by_normalized = {normalized(branch): branch for branch in branches}
    for candidate in candidates:
        if candidate in by_normalized:
            return by_normalized[candidate]
    return None


def read_exit_code(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def scan_gate_log(log_path: Path) -> tuple[str, bool, dict[str, list[str]]]:
    if not log_path.is_file():
        return "", True, {"missing_log": ["gate.log is missing"]}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    exact = [line for line in lines if "Failed to get the system corresponding to that digitizer" in line]
    fatal_exception = [line for line in lines if "Fatal Exception" in line]
    command_not_found = [line for line in lines if "COMMAND NOT FOUND" in line]
    macro_abort = [line for line in lines if "macro abort" in line.lower()]
    g4_exception = [line for line in lines if "G4Exception" in line]
    spatial = [line for line in lines if "GateSpatialResolution" in line]
    abort_context = [
        line
        for line in lines
        if "abort" in line.lower()
        and any(token in line.lower() for token in ("fatal", "exception", "macro", "command", "digitize"))
    ]
    findings = {
        "Fatal Exception": fatal_exception,
        "COMMAND NOT FOUND": command_not_found,
        "Failed to get the system corresponding to that digitizer": exact,
        "GateSpatialResolution": spatial,
        "macro abort": macro_abort,
        "G4Exception": g4_exception,
        "fatal abort context": abort_context,
    }
    fatal = bool(fatal_exception or command_not_found or exact or macro_abort or abort_context)
    if g4_exception and any(
        "fatal" in line.lower() or "abort" in line.lower() for line in g4_exception
    ):
        fatal = True
    return text, fatal, findings


def discover_root_files(output_dir: Path, production_dir: Path) -> list[Path]:
    candidates: set[Path] = set()
    for path in output_dir.glob("*.root"):
        if path.is_file():
            candidates.add(path.resolve())
    # Step 7 runs the one-second bounded main, whose output prefix is kept
    # separate from the real production prefix and historical timeout files.
    for path in production_dir.glob("magiccube_step7_bounded*.root"):
        if path.is_file():
            candidates.add(path.resolve())
    return sorted(candidates)


def infer_kind(file_name: str, tree_name: str) -> str:
    combined = f"{file_name} {tree_name}".lower()
    if "singles" in combined:
        return "Singles"
    if "hits" in combined or re.search(r"\bhit\b", combined):
        return "Hits"
    return "other"


def clean_key(key: Any) -> str:
    return str(key).split(";", 1)[0]


def inspect_root_files(paths: list[Path], uproot: Any) -> tuple[list[TreeRecord], list[str]]:
    records: list[TreeRecord] = []
    errors: list[str] = []
    for path in paths:
        try:
            root_file = uproot.open(path)
            for key, obj in root_file.items(recursive=True):
                if not hasattr(obj, "num_entries") or not hasattr(obj, "keys"):
                    continue
                tree_name = clean_key(key)
                branches = [clean_key(name) for name in obj.keys()]
                try:
                    raw_types = obj.typenames()
                    types = {clean_key(name): str(value) for name, value in raw_types.items()}
                except Exception:  # noqa: BLE001 - schema reporting is best effort
                    types = {}
                records.append(
                    TreeRecord(
                        path=path,
                        tree_name=tree_name,
                        kind=infer_kind(path.name, tree_name),
                        tree=obj,
                        branches=branches,
                        types=types,
                        entries=int(obj.num_entries),
                    )
                )
            # Keep the file-backed tree objects alive until identity inspection
            # has loaded their arrays.  The validator exits immediately after
            # reporting, so this bounded diagnostic does not need to retain
            # handles beyond the process lifetime.
        except Exception as exc:  # noqa: BLE001 - report per-file read failures
            errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    return records, errors


def load_detector_centers(path: Path) -> list[tuple[float, float, float]]:
    centers: list[tuple[float, float, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
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


def scalar_values(array: Any) -> list[float]:
    values: list[float] = []
    for value in array:
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            values.append(float(value[0]))
    return values


def position_arrays(record: TreeRecord) -> tuple[list[float], list[float], list[float]] | None:
    x_name = choose_branch(record.branches, POSITION_CANDIDATES["x"])
    y_name = choose_branch(record.branches, POSITION_CANDIDATES["y"])
    z_name = choose_branch(record.branches, POSITION_CANDIDATES["z"])
    if x_name and y_name and z_name:
        return (
            scalar_values(record.tree[x_name].array(library="np")),
            scalar_values(record.tree[y_name].array(library="np")),
            scalar_values(record.tree[z_name].array(library="np")),
        )

    vector_name = choose_branch(record.branches, VECTOR_POSITION_CANDIDATES)
    if vector_name:
        vector_values = record.tree[vector_name].array(library="np")
        x_values: list[float] = []
        y_values: list[float] = []
        z_values: list[float] = []
        for row in vector_values:
            if len(row) < 3:
                return None
            x_values.append(float(row[0]))
            y_values.append(float(row[1]))
            z_values.append(float(row[2]))
        return x_values, y_values, z_values
    return None


def identity_check(
    records: list[TreeRecord], map_path: Path
) -> tuple[str, dict[str, str], list[str]]:
    details: dict[str, str] = {}
    messages: list[str] = []
    try:
        centers = load_detector_centers(map_path)
    except Exception as exc:  # noqa: BLE001 - identity is a separate result
        return (
            "PRODUCTION_IDENTITY_RUNTIME_AMBIGUOUS",
            {},
            [f"detector_map.csv could not be loaded: {type(exc).__name__}: {exc}"],
        )

    per_kind: dict[str, dict[str, int]] = {
        "Hits": {"observations": 0, "mapped": 0, "unmapped": 0, "ambiguous": 0, "trees": 0},
        "Singles": {"observations": 0, "mapped": 0, "unmapped": 0, "ambiguous": 0, "trees": 0},
    }
    position_tree_found: dict[str, bool] = {"Hits": False, "Singles": False}
    for record in records:
        if record.kind not in per_kind:
            continue
        try:
            arrays = position_arrays(record)
        except Exception as exc:  # noqa: BLE001 - report per-tree identity issue
            messages.append(
                f"{record.kind}/{record.tree_name}: position read failed: {type(exc).__name__}: {exc}"
            )
            continue
        if arrays is None:
            continue
        position_tree_found[record.kind] = True
        per_kind[record.kind]["trees"] += 1
        xs, ys, zs = arrays
        for x_value, y_value, z_value in zip(xs, ys, zs):
            per_kind[record.kind]["observations"] += 1
            matches = sum(
                abs(x_value - center[0]) <= 1.01
                and abs(y_value - center[1]) <= 1.01
                and abs(z_value - center[2]) <= 1.01
                for center in centers
            )
            if matches == 1:
                per_kind[record.kind]["mapped"] += 1
            elif matches == 0:
                per_kind[record.kind]["unmapped"] += 1
            else:
                per_kind[record.kind]["ambiguous"] += 1

    for kind in ("Hits", "Singles"):
        stats = per_kind[kind]
        details[kind] = (
            f"trees={stats['trees']} observations={stats['observations']} "
            f"mapped={stats['mapped']} unmapped={stats['unmapped']} "
            f"ambiguous={stats['ambiguous']}"
        )
        if position_tree_found[kind]:
            messages.append(f"{kind} canonical identity: {details[kind]}")
        else:
            messages.append(f"{kind} canonical identity: NOT DIRECTLY AVAILABLE — position branches unavailable")

    hits_valid = (
        position_tree_found["Hits"]
        and per_kind["Hits"]["mapped"] > 0
        and per_kind["Hits"]["unmapped"] == 0
        and per_kind["Hits"]["ambiguous"] == 0
    )
    singles_valid = (
        position_tree_found["Singles"]
        and per_kind["Singles"]["mapped"] > 0
        and per_kind["Singles"]["unmapped"] == 0
        and per_kind["Singles"]["ambiguous"] == 0
    )
    any_position = position_tree_found["Hits"] or position_tree_found["Singles"]
    if hits_valid and singles_valid:
        status = "PRODUCTION_IDENTITY_VALIDATED"
    elif any_position:
        status = "PRODUCTION_IDENTITY_RUNTIME_AMBIGUOUS"
    else:
        status = "PRODUCTION_IDENTITY_OUTPUT_INSUFFICIENT"
    return status, details, messages


def write_schema_report(
    path: Path,
    output_dir: Path,
    production_dir: Path,
    records: list[TreeRecord],
    read_errors: list[str],
    identity_status: str,
    identity_details: dict[str, str],
) -> None:
    lines = [
        "Magic-Cube Step-7 ROOT schema report",
        "runtime_mode: BOUNDED VALIDATION",
        "simulated_acquisition: 1 s",
        "production_acquisition: 15 s",
        f"output_dir: {output_dir}",
        f"production_dir: {production_dir}",
        "No event rows are dumped; this file records tree metadata and branch schemas.",
        "",
    ]
    if not records:
        lines.append("No readable Hits/Singles trees were discovered.")
    for record in records:
        lines.append(f"FILE: {record.path}")
        lines.append(f"TREE: {record.tree_name}")
        lines.append(f"CLASS: {record.kind}")
        lines.append(f"ENTRIES: {record.entries}")
        lines.append("BRANCHES:")
        for branch in record.branches:
            lines.append(f"  {branch}: {record.types.get(branch, 'type unavailable')}")
        native = [
            branch
            for branch in record.branches
            if any(token in normalized(branch) for token in ("volumeid", "copy", "crystal", "detectorid", "eventid", "runid"))
        ]
        lines.append("NATIVE/EVENT CANDIDATES: " + (", ".join(native) if native else "none detected"))
        lines.append("")
    if read_errors:
        lines.append("ROOT READ ERRORS:")
        lines.extend(f"  {error}" for error in read_errors)
        lines.append("")
    lines.append(f"IDENTITY STATUS: {identity_status}")
    for kind, detail in identity_details.items():
        lines.append(f"IDENTITY {kind}: {detail}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--production-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    production_dir = args.production_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    exit_code = read_exit_code(output_dir / "gate_exit_code.txt")
    log_text, fatal, findings = scan_gate_log(output_dir / "gate.log")
    print("RUNTIME MODE: BOUNDED VALIDATION")
    print("- simulated acquisition: 1 s")
    print("- production acquisition: 15 s")
    print("GATE RUNTIME")
    print(f"- exit code: {exit_code if exit_code is not None else 'MISSING'}")
    for label, lines in findings.items():
        if lines:
            print(f"- {label}: {len(lines)} occurrence(s)")
    print(f"- fatal abort detected: {'YES' if fatal else 'NO'}")
    print(f"- GateSpatialResolution mentioned: {'YES' if findings['GateSpatialResolution'] else 'NO'}")

    roots = discover_root_files(output_dir, production_dir)
    print("ROOT FILE DISCOVERY")
    for root in roots:
        print(f"- candidate: {root}")
    if not roots:
        print("- no production ROOT files discovered")

    try:
        import uproot  # type: ignore
    except Exception as exc:  # noqa: BLE001 - environment is a reported result
        print("ROOT CONTENT CHECK: NOT PERFORMED — VALIDATOR ENVIRONMENT ERROR")
        print(f"- uproot import: {type(exc).__name__}: {exc}")
        (output_dir / "step7_root_schema.txt").write_text(
            "ROOT CONTENT CHECK: NOT PERFORMED — VALIDATOR ENVIRONMENT ERROR\n",
            encoding="utf-8",
        )
        if exit_code == 0 and not fatal:
            classification = "STEP7_VALIDATION_ENVIRONMENT_ERROR"
        else:
            classification = "STEP7_PRODUCTION_RUNTIME_FAILED"
        print(f"FINAL CLASSIFICATION: {classification}")
        print("IDENTITY CLASSIFICATION: PRODUCTION_IDENTITY_NOT_CHECKED_ENVIRONMENT_ERROR")
        return 1

    records, read_errors = inspect_root_files(roots, uproot)
    hits = [record for record in records if record.kind == "Hits"]
    singles = [record for record in records if record.kind == "Singles"]
    other = [record for record in records if record.kind == "other"]
    print("HITS")
    for record in hits:
        print(f"- {record.path.name} | tree={record.tree_name} | entries={record.entries}")
    print(f"- total Hits: {sum(record.entries for record in hits)}")
    print("SINGLES")
    for record in singles:
        print(f"- {record.path.name} | tree={record.tree_name} | entries={record.entries}")
    print(f"- total Singles: {sum(record.entries for record in singles)}")
    if other:
        print("OTHER ROOT OBJECTS")
        for record in other:
            print(f"- {record.path.name} | tree={record.tree_name} | entries={record.entries}")
    if read_errors:
        print("ROOT READ ERRORS")
        for error in read_errors:
            print(f"- {error}")

    print("ROOT SCHEMA")
    for record in records:
        print(f"- {record.kind}: {record.path.name} :: {record.tree_name}")
        for branch in record.branches:
            print(f"    {branch}: {record.types.get(branch, 'type unavailable')}")

    identity_status, identity_details, identity_messages = identity_check(
        records, Path(__file__).resolve().parent / "detector_map.csv"
    )
    for message in identity_messages:
        print(message)
    write_schema_report(
        output_dir / "step7_root_schema.txt",
        output_dir,
        production_dir,
        records,
        read_errors,
        identity_status,
        identity_details,
    )
    # The schema report is runtime evidence kept inside the Step-7 directory.

    total_hits = sum(record.entries for record in hits)
    total_singles = sum(record.entries for record in singles)
    if exit_code != 0 or exit_code is None or fatal:
        classification = "STEP7_PRODUCTION_RUNTIME_FAILED"
    elif total_hits == 0 or total_singles == 0:
        classification = "STEP7_OUTPUT_EMPTY"
    elif identity_status == "PRODUCTION_IDENTITY_VALIDATED":
        classification = "STEP7_END_TO_END_VALIDATED"
    else:
        classification = "STEP7_RUNTIME_VALID_IDENTITY_PENDING"
    print(f"POSITION MAPPING: {identity_status}")
    print(f"FINAL CLASSIFICATION: {classification}")
    print(f"IDENTITY CLASSIFICATION: {identity_status}")

    # Only a fully end-to-end result is a successful Step-7 validator result.
    return 0 if classification == "STEP7_END_TO_END_VALIDATED" else 1


if __name__ == "__main__":
    sys.exit(main())
