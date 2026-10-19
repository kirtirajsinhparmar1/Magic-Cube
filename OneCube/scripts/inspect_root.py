#!/usr/bin/env python3
"""Inspect the two merged GATE ROOT trees and write a compact JSON summary."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
import uproot


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "onecube_config.json"
MERGED_DIR = PROJECT_ROOT / "runtime" / "merged"
SUMMARY_PATH = PROJECT_ROOT / "results" / "validation" / "root_summary.json"


def load_config() -> Dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def _bare_key(key: Any) -> str:
    return str(key).split(";", 1)[0]


def _normalise_name(name: Any) -> str:
    return "".join(character.lower() for character in str(name) if character.isalnum())


def find_tree(root_file: Any) -> Tuple[str, Any]:
    """Return the first TTree-like object, preferring the conventional tree names."""

    candidates = []
    for key, obj in root_file.items(recursive=True):
        if hasattr(obj, "arrays") and hasattr(obj, "num_entries"):
            name = _bare_key(key)
            candidates.append((name, obj))
    if not candidates:
        raise ValueError("ROOT file contains no readable TTree")

    preferred = {"tree": 0, "hits": 1, "singles": 2}
    candidates.sort(key=lambda item: (preferred.get(item[0].lower(), 10), item[0]))
    return candidates[0]


def read_tree(path: Path) -> Dict[str, Any]:
    """Read one ROOT tree into a dataframe and retain inspection metadata."""

    if not path.is_file():
        raise FileNotFoundError(str(path))
    if path.stat().st_size <= 100:
        raise ValueError("ROOT file is smaller than a minimal ROOT header")

    with uproot.open(path) as root_file:
        tree_name, tree = find_tree(root_file)
        frame = tree.arrays(library="pd")
        if not isinstance(frame, pd.DataFrame):
            frame = pd.DataFrame(frame)
        branches = [str(branch) for branch in tree.keys()]
        dtypes = {str(column): str(frame[column].dtype) for column in frame.columns}
        return {
            "file": str(path),
            "tree_name": tree_name,
            "entry_count": int(tree.num_entries),
            "branch_names": branches,
            "branch_dtypes": dtypes,
            "frame": frame,
        }


def find_branch(frame: pd.DataFrame, names: Iterable[str]) -> Optional[str]:
    by_normalised = {_normalise_name(column): str(column) for column in frame.columns}
    for name in names:
        match = by_normalised.get(_normalise_name(name))
        if match is not None:
            return match
    return None


def numeric_values(frame: pd.DataFrame, column: str) -> np.ndarray:
    values = np.asarray(frame[column].to_numpy(), dtype=np.float64)
    return values[np.isfinite(values)]


def coordinate_summary(frame: pd.DataFrame, names: Iterable[str]) -> Dict[str, Any]:
    column = find_branch(frame, names)
    if column is None:
        return {"present": False, "column": None}
    values = numeric_values(frame, column)
    if values.size == 0:
        return {"present": True, "column": column, "finite_values": 0}
    return {
        "present": True,
        "column": column,
        "finite_values": int(values.size),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def hit_position_report(frame: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    detector = config["detector"]
    coordinate_names = {
        "x": ("posX", "globalPosX"),
        "y": ("posY", "globalPosY"),
        "z": ("posZ", "globalPosZ"),
    }
    report = {
        axis: coordinate_summary(frame, names) for axis, names in coordinate_names.items()
    }
    if not all(report[axis]["present"] for axis in coordinate_names):
        report["within_detector"] = None
        return report

    within = True
    for axis, names in coordinate_names.items():
        values = numeric_values(frame, find_branch(frame, names))
        half_size = float(detector[f"size_{axis}_mm"]) / 2.0
        centre = float(detector[f"{axis}_mm"])
        within = within and bool(
            values.size == len(frame)
            and np.all(np.abs(values - centre) <= half_size + 1.0e-6)
        )
    report["within_detector"] = within
    return report


def source_position_report(frame: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    source = config["source"]
    coordinate_names = {
        "x": ("sourcePosX",),
        "y": ("sourcePosY",),
        "z": ("sourcePosZ",),
    }
    report = {
        axis: coordinate_summary(frame, names) for axis, names in coordinate_names.items()
    }
    if not all(report[axis]["present"] for axis in coordinate_names):
        report["matches_config"] = None
        return report

    matches = True
    for axis, names in coordinate_names.items():
        values = numeric_values(frame, find_branch(frame, names))
        expected = float(source[f"{axis}_mm"])
        matches = matches and bool(values.size == len(frame) and np.allclose(values, expected))
    report["matches_config"] = matches
    return report


def event_identity_report(frame: pd.DataFrame) -> Dict[str, Any]:
    run_column = find_branch(frame, ("runID",))
    event_column = find_branch(frame, ("eventID",))
    return {
        "runID_present": run_column is not None,
        "eventID_present": event_column is not None,
        "join_key": [name for name, column in (("runID", run_column), ("eventID", event_column)) if column],
    }


def inspect_merged() -> Tuple[Dict[str, Any], list]:
    config = load_config()
    paths = {"hits": MERGED_DIR / "hits.root", "singles": MERGED_DIR / "singles.root"}
    files: Dict[str, Any] = {}
    failures = []

    for kind, path in paths.items():
        try:
            info = read_tree(path)
            frame = info.pop("frame")
            if info["entry_count"] <= 0:
                failures.append(f"{kind} tree has zero entries")
            report: Dict[str, Any] = {
                **info,
                "event_identity": event_identity_report(frame),
            }
            if kind == "hits":
                report["edep"] = coordinate_summary(frame, ("edep", "energyDeposit"))
                report["positions"] = hit_position_report(frame, config)
                report["source_positions"] = source_position_report(frame, config)
                if report["positions"].get("within_detector") is not True:
                    failures.append("Hits positions are missing or outside the 2 mm detector cube")
            else:
                report["source_positions"] = source_position_report(frame, config)
            files[kind] = report
        except Exception as error:  # noqa: BLE001 - convert inspection failures to concrete checks
            failures.append(f"{kind} ROOT inspection failed: {error}")

    summary = {
        "config_path": str(CONFIG_PATH),
        "files": files,
        "hits_count": files.get("hits", {}).get("entry_count", 0),
        "singles_count": files.get("singles", {}).get("entry_count", 0),
        "canonical_detector_ids": [int(config["detector"]["detector_id"])],
        "canonical_source_ids": [int(config["source"]["source_id"])],
        "event_join_policy": "runID + eventID when diagnostic matching is needed; Singles count is primary",
        "failures": failures,
    }
    return summary, failures


def main() -> int:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        summary, failures = inspect_merged()
    except Exception as error:  # noqa: BLE001 - make CLI failure actionable
        summary = {"failures": [f"ROOT inspection setup failed: {error}"]}
        failures = summary["failures"]
    with SUMMARY_PATH.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")

    if failures:
        for failure in failures:
            print(f"FAILED: {failure}")
        return 1
    print("ROOT inspection: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
