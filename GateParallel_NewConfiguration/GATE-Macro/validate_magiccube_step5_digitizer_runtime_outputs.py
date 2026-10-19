#!/usr/bin/env python3
"""Validate the bounded Step-5 production digitizer runtime output."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any


def read_exit_code(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def classify_tree(filename: str, tree_name: str) -> str:
    text = f"{filename} {tree_name}".lower()
    if "singles" in text:
        return "singles"
    if "hits" in text or "hit" in text:
        return "hits"
    return "other"


def inspect_roots(output_dir: Path, uproot: Any) -> tuple[int, int, bool, bool]:
    hits = 0
    singles = 0
    readable = True
    any_root = False
    roots = sorted(output_dir.glob("*.root"))
    print("ROOT files:")
    if not roots:
        print("  NONE")
    for path in roots:
        any_root = True
        try:
            with uproot.open(path) as root_file:
                classnames = root_file.classnames(recursive=True)
                found_tree = False
                for key, class_name in classnames.items():
                    if not str(class_name).startswith("TTree"):
                        continue
                    found_tree = True
                    tree_name = str(key).split(";", 1)[0]
                    entries = int(root_file[tree_name].num_entries)
                    kind = classify_tree(path.name, tree_name)
                    print(f"  {kind.upper()} {path.name} :: {tree_name} entries={entries}")
                    if kind == "hits":
                        hits += entries
                    elif kind == "singles":
                        singles += entries
                if not found_tree:
                    print(f"  {path.name}: no TTree found")
        except Exception as exc:  # noqa: BLE001 - report ROOT read failures
            readable = False
            print(f"  ROOT READ ERROR {path.name}: {type(exc).__name__}: {exc}")
    return hits, singles, readable, any_root


def fatal_lines(log_text: str) -> list[str]:
    matches: list[str] = []
    for line in log_text.splitlines():
        lower = line.lower()
        fatal = (
            "fatal exception" in lower
            or "command not found" in lower
            or "failed to get the system corresponding to that digitizer" in lower
            or ("g4exception" in lower and ("abort" in lower or "fatal" in lower))
            or (
                "abort" in lower
                and any(token in lower for token in ("error", "exception", "macro", "sorry", "fatal"))
            )
        )
        if fatal:
            matches.append(line.strip())
    return matches


def position_mapping_note(output_dir: Path, uproot: Any) -> None:
    """Keep identity out of the hard gate while reporting branch availability."""
    position_names = {
        "globalposx",
        "globalpositionx",
        "globalx",
        "globalposy",
        "globalpositiony",
        "globaly",
        "globalposz",
        "globalpositionz",
        "globalz",
    }
    for path in sorted(output_dir.glob("*.root")):
        try:
            with uproot.open(path) as root_file:
                for key, class_name in root_file.classnames(recursive=True).items():
                    if not str(class_name).startswith("TTree"):
                        continue
                    tree_name = str(key).split(";", 1)[0]
                    branches = {
                        re.sub(r"[^a-z0-9]", "", str(name).lower())
                        for name in root_file[tree_name].keys()
                    }
                    if position_names.intersection(branches):
                        print(
                            "POSITION MAPPING: NOT PERFORMED — optional for this test; "
                            "POSITION_DERIVED_REQUIRED remains frozen"
                        )
                        return
        except Exception:
            print("POSITION MAPPING: NOT PERFORMED — ROOT branch inspection failed")
            return
    print("POSITION MAPPING: NOT PERFORMED — suitable position branches unavailable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir
    exit_path = output_dir / "gate_exit_code.txt"
    gate_exit = read_exit_code(exit_path)
    log_path = output_dir / "gate.log"
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        log_text = ""

    print("GATE:")
    print(f"- exit code: {gate_exit if gate_exit is not None else 'MISSING'}")
    print(f"- GateSpatialResolution mentioned: {'YES' if 'GateSpatialResolution' in log_text else 'NO'}")
    spatial_lookup = "Failed to get the system corresponding to that digitizer" in log_text
    print(f"- corresponding-system failure: {'YES' if spatial_lookup else 'NO'}")
    failures = fatal_lines(log_text)
    print(f"- fatal/error patterns: {len(failures)}")
    for line in failures[:20]:
        print(f"  {line}")

    try:
        import uproot  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - distinguish environment failure
        print(f"ROOT CONTENT CHECK: NOT PERFORMED — VALIDATOR ENVIRONMENT ERROR: {exc}")
        print("FINAL CLASSIFICATION: VALIDATION_INCOMPLETE_ENVIRONMENT_ERROR")
        return 2

    hits, singles, readable, any_root = inspect_roots(output_dir, uproot)
    print(f"Total Hits entries: {hits}")
    print(f"Total Singles entries: {singles}")
    position_mapping_note(output_dir, uproot)

    if not readable:
        classification = "VALIDATION_INCOMPLETE_ENVIRONMENT_ERROR"
    elif gate_exit != 0:
        classification = (
            "SPATIALRESOLUTION_RUNTIME_BLOCKED"
            if spatial_lookup or any(
                "gatespatialresolution" in line.lower() and "exception" in line.lower()
                for line in failures
            )
            else "EARLIER_RUNTIME_FAILURE"
        )
    elif not any_root:
        classification = "EARLIER_RUNTIME_FAILURE"
    elif hits == 0:
        classification = "RAW_HITS_LOST_WITH_DIGITIZER_PRESENT"
    elif singles == 0:
        classification = "HITS_PRESENT_BUT_NO_SINGLES"
    else:
        classification = "DIGITIZER_RUNTIME_VALIDATED"

    print(f"FINAL CLASSIFICATION: {classification}")
    return 0 if classification == "DIGITIZER_RUNTIME_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
