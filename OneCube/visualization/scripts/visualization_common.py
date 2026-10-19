"""Shared path, ROOT, configuration, and plotting data helpers for OneCube.

The scientific configuration remains in ``../config/onecube_config.json``.
This module only supplies visualization plumbing and branch discovery; it does
not infer detector identity from native GATE volumeID fields.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import uproot


VISUALIZATION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIS_CONFIG = VISUALIZATION_ROOT / "config" / "visualization_config.json"


class VisualizationError(RuntimeError):
    """A clear, user-actionable visualization failure."""


def resolve_path(raw: str | Path, base: Path) -> Path:
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def load_configs(config_path: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Path]:
    """Load visualization settings and the existing OneCube source config."""

    visual_path = Path(config_path).expanduser().resolve() if config_path else DEFAULT_VIS_CONFIG
    if not visual_path.is_file():
        raise VisualizationError(f"visualization config does not exist: {visual_path}")
    visual = json.loads(visual_path.read_text())
    source_path = resolve_path(visual["source_config"], visual_path.parent)
    if not source_path.is_file():
        raise VisualizationError(f"OneCube source config does not exist: {source_path}")
    source = json.loads(source_path.read_text())
    return visual, source, source_path


def output_dir(visual: dict[str, Any], config_path: str | Path | None = None) -> Path:
    visual_path = Path(config_path).expanduser().resolve() if config_path else DEFAULT_VIS_CONFIG
    path = resolve_path(visual["output_dir"], visual_path.parent)
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_dir(visual: dict[str, Any], config_path: str | Path | None = None) -> Path:
    visual_path = Path(config_path).expanduser().resolve() if config_path else DEFAULT_VIS_CONFIG
    path = resolve_path(visual["runtime_dir"], visual_path.parent)
    path.mkdir(parents=True, exist_ok=True)
    return path


def input_candidates(
    visual: dict[str, Any], kind: str, config_path: str | Path | None = None
) -> list[Path]:
    visual_path = Path(config_path).expanduser().resolve() if config_path else DEFAULT_VIS_CONFIG
    return [resolve_path(item, visual_path.parent) for item in visual["input_candidates"][kind]]


def find_input(
    visual: dict[str, Any], kind: str, config_path: str | Path | None = None
) -> Path:
    candidates = input_candidates(visual, kind, config_path)
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    formatted = ", ".join(str(item) for item in candidates)
    raise VisualizationError(f"no readable {kind} ROOT input found; checked: {formatted}")


def find_tree(root_file: uproot.ReadOnlyFile) -> tuple[str, Any]:
    for key, obj in root_file.items(recursive=True):
        if hasattr(obj, "num_entries") and hasattr(obj, "arrays") and hasattr(obj, "keys"):
            return str(key).split(";", 1)[0], obj
    raise VisualizationError("ROOT file contains no readable TTree")


def load_root_dataframe(
    visual: dict[str, Any], kind: str, config_path: str | Path | None = None
) -> dict[str, Any]:
    """Read one ROOT TTree and return its dataframe plus immutable metadata."""

    path = find_input(visual, kind, config_path)
    try:
        with uproot.open(path) as root_file:
            tree_name, tree = find_tree(root_file)
            frame = tree.arrays(library="pd")
            entries = int(tree.num_entries)
    except Exception as exc:  # noqa: BLE001 - convert library errors to context
        raise VisualizationError(f"could not read {kind} ROOT file {path}: {exc}") from exc
    if entries <= 0:
        raise VisualizationError(f"{kind} ROOT tree {path}:{tree_name} has zero entries")
    return {
        "kind": kind,
        "path": path,
        "tree_name": tree_name,
        "entries": entries,
        "frame": frame,
        "branch_names": [str(column) for column in frame.columns],
        "branch_dtypes": {str(column): str(frame[column].dtype) for column in frame.columns},
    }


ALIASES: dict[str, tuple[str, ...]] = {
    "x": ("posX", "globalPosX", "localPosX", "x"),
    "y": ("posY", "globalPosY", "localPosY", "y"),
    "z": ("posZ", "globalPosZ", "localPosZ", "z"),
    "source_x": ("sourcePosX",),
    "source_y": ("sourcePosY",),
    "source_z": ("sourcePosZ",),
    "edep": ("edep", "energyDeposit", "depositedEnergy"),
    "energy": ("energy", "edep", "energyDeposit"),
    "time": ("time", "globalTime", "trackLocalTime", "localTime"),
    "event_id": ("eventID", "eventId", "event"),
    "run_id": ("runID", "runId", "run"),
    "source_id": ("sourceID", "sourceId"),
}


def find_column(frame: pd.DataFrame, semantic_name: str) -> str | None:
    for candidate in ALIASES.get(semantic_name, (semantic_name,)):
        if candidate in frame.columns:
            return candidate
    return None


def numeric_column(frame: pd.DataFrame, semantic_name: str) -> tuple[str | None, np.ndarray | None]:
    column = find_column(frame, semantic_name)
    if column is None:
        return None, None
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    return column, values


def finite_values(frame: pd.DataFrame, semantic_name: str) -> tuple[str | None, np.ndarray]:
    column, values = numeric_column(frame, semantic_name)
    if values is None:
        return column, np.asarray([], dtype=float)
    return column, values[np.isfinite(values)]


def xyz_arrays(data: dict[str, Any]) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
    frame = data["frame"]
    names: list[str] = []
    arrays: list[np.ndarray] = []
    for semantic in ("x", "y", "z"):
        column, values = numeric_column(frame, semantic)
        if column is None or values is None:
            raise VisualizationError(
                f"{data['kind']} ROOT data lacks a usable {semantic} position branch"
            )
        names.append(column)
        arrays.append(values)
    finite = np.isfinite(arrays[0]) & np.isfinite(arrays[1]) & np.isfinite(arrays[2])
    if not np.any(finite):
        raise VisualizationError(f"{data['kind']} position branches contain no finite coordinates")
    return ",".join(names), arrays[0][finite], arrays[1][finite], arrays[2][finite]


def cube_bounds(source: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    detector = source["detector"]
    center = np.array([detector["x_mm"], detector["y_mm"], detector["z_mm"]], dtype=float)
    size = np.array([detector["size_x_mm"], detector["size_y_mm"], detector["size_z_mm"]], dtype=float)
    return center - size / 2.0, center + size / 2.0


def cube_center_size(source: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    detector = source["detector"]
    center = np.array([detector["x_mm"], detector["y_mm"], detector["z_mm"]], dtype=float)
    size = np.array([detector["size_x_mm"], detector["size_y_mm"], detector["size_z_mm"]], dtype=float)
    return center, size


def canonical_detector_ids(source: dict[str, Any], count: int) -> list[int]:
    """OneCube identity is the configured sensitive collection, always ID zero."""

    if source["detector"]["count"] != 1 or source["detector"]["detector_id"] != 0:
        raise VisualizationError("visualization package requires OneCube detector count=1 and ID=0")
    return [0] * int(count)


def finite_min_max(values: np.ndarray) -> dict[str, Any]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"present": False, "finite_values": 0}
    return {
        "present": True,
        "finite_values": int(finite.size),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
    }


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path).write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n")


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise VisualizationError(f"required CSV does not exist: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise VisualizationError(f"could not parse {label} as a number: {value!r}") from exc
    if not math.isfinite(result):
        raise VisualizationError(f"{label} is not finite: {value!r}")
    return result


def format_mm(value: float) -> str:
    return f"{value:g} mm"


def format_count(value: int | float) -> str:
    return f"{int(value):,}"
