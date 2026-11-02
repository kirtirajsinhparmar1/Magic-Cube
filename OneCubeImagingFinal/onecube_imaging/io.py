from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


def load_config(project_root: Path) -> dict[str, Any]:
    path = project_root / "config" / "imaging_config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    _write_preserving(path, payload.encode("utf-8"))


def write_runtime_json(path: Path, value: Any) -> None:
    """Atomically replace mutable runtime status/provenance records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})
        temporary = Path(stream.name)
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def save_npy(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        np.save(stream, np.asarray(array))
        temporary = Path(stream.name)
    os.replace(temporary, path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_generated_text(path: Path, contents: str) -> None:
    """Create deterministic preparation artifacts without replacing changed files."""
    _write_preserving(path, contents.encode("utf-8"))


def _write_preserving(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"Refusing to overwrite changed preparation/runtime input: {path}")
        return
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, separators=(",", ":"))
    if isinstance(value, np.generic):
        return value.item()
    return value


def root_tree_entries(path: Path) -> int:
    """Read an accepted event count without materializing all ROOT branches."""
    import uproot

    if not path.is_file() or path.stat().st_size <= 100:
        raise ValueError(f"ROOT output is absent or too small: {path}")
    with uproot.open(path) as root_file:
        candidates = []
        for key, obj in root_file.items(recursive=True):
            if hasattr(obj, "num_entries") and hasattr(obj, "arrays"):
                name = str(key).split(";", 1)[0].lower()
                candidates.append((0 if name == "singles" else 1, int(obj.num_entries)))
        if not candidates:
            raise ValueError(f"No readable TTree in {path}")
        candidates.sort()
        return candidates[0][1]
