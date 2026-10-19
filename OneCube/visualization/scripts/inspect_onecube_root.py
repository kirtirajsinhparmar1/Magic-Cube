#!/usr/bin/env python3
"""Inspect the existing OneCube Hits and Singles ROOT products."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from visualization_common import (
    VisualizationError,
    cube_bounds,
    find_column,
    finite_min_max,
    finite_values,
    load_configs,
    load_root_dataframe,
    numeric_column,
    output_dir,
    runtime_dir,
    write_json,
    xyz_arrays,
)


def _field_summary(data: dict, semantic_name: str) -> dict:
    column, values = finite_values(data["frame"], semantic_name)
    summary = finite_min_max(values)
    summary["column"] = column
    return summary


def _position_summary(data: dict, source: dict) -> dict:
    frame = data["frame"]
    result: dict = {}
    coordinate_arrays: list[np.ndarray] = []
    for semantic in ("x", "y", "z"):
        column, values = numeric_column(frame, semantic)
        summary = finite_min_max(values if values is not None else np.asarray([], dtype=float))
        summary["column"] = column
        result[semantic] = summary
        if values is not None:
            coordinate_arrays.append(values)
    if len(coordinate_arrays) == 3:
        finite = np.isfinite(coordinate_arrays[0])
        finite &= np.isfinite(coordinate_arrays[1])
        finite &= np.isfinite(coordinate_arrays[2])
        lower, upper = cube_bounds(source)
        inside = (
            (coordinate_arrays[0] >= lower[0] - 1e-6)
            & (coordinate_arrays[0] <= upper[0] + 1e-6)
            & (coordinate_arrays[1] >= lower[1] - 1e-6)
            & (coordinate_arrays[1] <= upper[1] + 1e-6)
            & (coordinate_arrays[2] >= lower[2] - 1e-6)
            & (coordinate_arrays[2] <= upper[2] + 1e-6)
        )
        result["finite_coordinates"] = int(np.count_nonzero(finite))
        result["within_detector"] = bool(np.all(inside[finite])) if np.any(finite) else False
    else:
        result["finite_coordinates"] = 0
        result["within_detector"] = False
    return result


def _source_position_summary(data: dict, source: dict) -> dict:
    expected = np.array(
        [source["source"]["x_mm"], source["source"]["y_mm"], source["source"]["z_mm"]],
        dtype=float,
    )
    arrays: list[np.ndarray] = []
    fields: dict = {}
    for semantic, expected_value in zip(("source_x", "source_y", "source_z"), expected):
        column, values = numeric_column(data["frame"], semantic)
        fields[semantic] = {"column": column, **finite_min_max(values if values is not None else np.array([]))}
        if values is not None:
            arrays.append(values)
    matches = False
    if len(arrays) == 3:
        finite = np.isfinite(arrays[0]) & np.isfinite(arrays[1]) & np.isfinite(arrays[2])
        matches = bool(
            np.any(finite)
            and np.allclose(
                np.column_stack([arrays[0][finite], arrays[1][finite], arrays[2][finite]]),
                expected,
                atol=1e-5,
            )
        )
    return {**fields, "matches_config": matches}


def _identity_summary(data: dict) -> dict:
    frame = data["frame"]
    source_column = find_column(frame, "source_id")
    source_values: list[int] = []
    if source_column is not None:
        values = np.asarray(frame[source_column], dtype=float)
        finite = values[np.isfinite(values)]
        source_values = sorted({int(value) for value in finite})
    return {
        "canonical_detector_id": 0,
        "canonical_detector_ids": [0] * int(data["entries"]),
        "source_id_column": source_column,
        "source_ids": source_values,
    }


def summarize(data: dict, source: dict) -> dict:
    frame = data["frame"]
    run_column = find_column(frame, "run_id")
    event_column = find_column(frame, "event_id")
    return {
        "file": str(data["path"]),
        "tree_name": data["tree_name"],
        "entry_count": int(data["entries"]),
        "branch_names": data["branch_names"],
        "branch_dtypes": data["branch_dtypes"],
        "event_identity": {
            "runID_present": run_column is not None,
            "eventID_present": event_column is not None,
            "join_key": [name for name, present in (("runID", run_column), ("eventID", event_column)) if present],
        },
        "edep": _field_summary(data, "edep"),
        "energy": _field_summary(data, "energy"),
        "time": _field_summary(data, "time"),
        "positions": _position_summary(data, source),
        "source_positions": _source_position_summary(data, source),
        "identity": _identity_summary(data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, source_path = load_configs(args.config)
        hits = load_root_dataframe(visual, "hits", args.config)
        singles = load_root_dataframe(visual, "singles", args.config)
        payload = {
            "source_config": str(source_path),
            "detector_id_contract": {"detector_count": 1, "canonical_detector_ids": [0]},
            "source_id_contract": {"source_count": 1, "source_ids": [0]},
            "hits": summarize(hits, source),
            "singles": summarize(singles, source),
            "animation": {
                "trajectory_data_present": False,
                "truthful_basis": "time branch if available; otherwise ROOT entry order",
                "warning": "hit buildup is not a reconstructed photon trajectory",
            },
        }
        path = runtime_dir(visual, args.config) / "root_inspection.json"
        write_json(path, payload)
        print(f"ROOT inspection written: {path}")
        print(f"Hits entries: {payload['hits']['entry_count']}")
        print(f"Singles entries: {payload['singles']['entry_count']}")
        print(f"Hits position branches: {payload['hits']['positions']['x']['column']}, "
              f"{payload['hits']['positions']['y']['column']}, "
              f"{payload['hits']['positions']['z']['column']}")
        print(f"Singles position branches: {payload['singles']['positions']['x']['column']}, "
              f"{payload['singles']['positions']['y']['column']}, "
              f"{payload['singles']['positions']['z']['column']}")
        return 0
    except (VisualizationError, OSError, ValueError) as exc:
        print(f"ROOT inspection FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
