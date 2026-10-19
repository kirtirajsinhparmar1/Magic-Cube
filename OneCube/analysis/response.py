"""Load the OneCube system response without embedding scanner geometry."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SystemResponse:
    """Response contract: rows are measurement bins; columns are image voxels."""

    matrix_cps_per_bq: np.ndarray
    measurement_ids: list[str]
    detector_ids: list[int | str]
    source_ids: list[int | str]
    source_coords_mm: np.ndarray
    detector_coords_mm: np.ndarray
    raw_counts: np.ndarray
    metadata: dict[str, Any]
    acquisition_s: float
    activity_bq: float | None

    @property
    def projection_operator_counts_per_bq(self) -> np.ndarray:
        """Convert rate response into expected counts for this acquisition."""
        return self.matrix_cps_per_bq * self.acquisition_s


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _id_key(value: Any) -> int | str:
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def _detector_positions(scanner: dict[str, Any], detector_ids: list[int | str]) -> np.ndarray:
    """Read detector positions from configuration, accepting list or legacy-map form."""
    detectors = scanner.get("detectors")
    if isinstance(detectors, list):
        by_id = { _id_key(d["detector_id"]): d for d in detectors }
    elif isinstance(scanner.get("detector"), dict):
        detector = scanner["detector"]
        by_id = {_id_key(detector.get("detector_id", detector_ids[0] if detector_ids else 0)): detector}
    else:
        by_id = {}
    positions = []
    for detector_id in detector_ids:
        detector = by_id.get(_id_key(detector_id))
        if detector is None:
            raise ValueError(f"No configured position for detector ID {detector_id!r}")
        positions.append([float(detector[f"{axis}_mm"]) for axis in ("x", "y", "z")])
    return np.asarray(positions, dtype=float)


def load_system_response(
    matrix_path: str | Path,
    metadata_path: str | Path,
    table_path: str | Path,
    scanner_config_path: str | Path,
) -> SystemResponse:
    """Load validated OneCube artifacts and preserve their declared ordering."""
    matrix = np.asarray(np.load(matrix_path), dtype=float)
    metadata = _read_json(Path(metadata_path))
    scanner = _read_json(Path(scanner_config_path))
    detector_ids = [_id_key(v) for v in metadata["detector_ids"]]
    source_ids = [_id_key(v) for v in metadata["source_ids"]]
    if matrix.ndim != 2 or matrix.shape != (len(detector_ids), len(source_ids)):
        raise ValueError("System matrix dimensions do not match metadata detector/source ordering")

    rows: list[dict[str, str]] = []
    with Path(table_path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    coords: dict[int | str, tuple[float, float, float]] = {}
    raw_counts = np.zeros(matrix.shape, dtype=float)
    raw_seen = np.zeros(matrix.shape, dtype=bool)
    row_index = {_id_key(value): i for i, value in enumerate(detector_ids)}
    col_index = {_id_key(value): j for j, value in enumerate(source_ids)}
    table_activity: list[float] = []
    table_duration: list[float] = []
    for row in rows:
        detector_id = _id_key(row["detector_id"])
        source_id = _id_key(row["source_id"])
        if detector_id not in row_index or source_id not in col_index:
            continue
        xyz = tuple(float(row[f"source_{axis}_mm"]) for axis in ("x", "y", "z"))
        previous = coords.setdefault(source_id, xyz)
        if not np.allclose(previous, xyz, rtol=0, atol=1e-9):
            raise ValueError(f"Source ID {source_id!r} maps to multiple coordinates")
        i, j = row_index[detector_id], col_index[source_id]
        if raw_seen[i, j]:
            raise ValueError(f"Duplicate detector/source table row for ({detector_id}, {source_id})")
        raw_counts[i, j] = float(row["raw_singles_count"])
        raw_seen[i, j] = True
        if row.get("activity_Bq"):
            table_activity.append(float(row["activity_Bq"]))
        if row.get("acquisition_s"):
            table_duration.append(float(row["acquisition_s"]))
    if set(coords) != set(source_ids):
        raise ValueError("System matrix source ordering is not fully represented in the source table")
    if not raw_seen.all():
        raise ValueError("Raw-count table does not cover every system-matrix element")
    source_coords = np.asarray([coords[source_id] for source_id in source_ids], dtype=float)

    acquisition_s = float(metadata.get("acquisition_s", scanner.get("acquisition", {}).get("duration_s", 0)))
    if acquisition_s <= 0 and table_duration:
        acquisition_s = table_duration[0]
    if acquisition_s <= 0:
        raise ValueError("A positive acquisition duration is required for count-rate projection")
    activity = metadata.get("activity_Bq", table_activity[0] if table_activity else None)
    activity_bq = float(activity) if activity is not None else None
    if activity_bq is not None and activity_bq <= 0:
        raise ValueError("Activity metadata must be positive")
    detector_coords = _detector_positions(scanner, detector_ids)
    measurement_ids = metadata.get("measurement_ids")
    if measurement_ids is None:
        measurement_ids = [f"measurement_bin:{i}" for i in range(matrix.shape[0])]
    measurement_ids = [str(value) for value in measurement_ids]
    if len(measurement_ids) != matrix.shape[0]:
        raise ValueError("measurement_ids length does not match system-matrix rows")

    if not np.isfinite(matrix).all() or (matrix < 0).any():
        raise ValueError("System response must contain finite, nonnegative values")
    if not np.isfinite(raw_counts).all() or (raw_counts < 0).any():
        raise ValueError("Raw count table must contain finite, nonnegative values")
    return SystemResponse(
        matrix_cps_per_bq=matrix,
        measurement_ids=measurement_ids,
        detector_ids=detector_ids,
        source_ids=source_ids,
        source_coords_mm=source_coords,
        detector_coords_mm=detector_coords,
        raw_counts=raw_counts,
        metadata=metadata,
        acquisition_s=acquisition_s,
        activity_bq=activity_bq,
    )
