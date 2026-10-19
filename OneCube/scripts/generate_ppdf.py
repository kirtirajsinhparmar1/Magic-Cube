#!/usr/bin/env python3
"""Generate the one-row OneCube detector-conditioned PPDF contract."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from inspect_root import load_config, read_tree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SINGLES_PATH = PROJECT_ROOT / "runtime" / "merged" / "singles.root"
OUTPUT_DIR = PROJECT_ROOT / "results" / "ppdf"


def main() -> int:
    config = load_config()
    detector = config["detector"]
    source = config["source"]
    if int(detector["count"]) != 1 or int(source["source_count"]) != 1:
        raise ValueError("OneCube PPDF requires exactly one detector and one source")

    info = read_tree(SINGLES_PATH)
    raw_count = int(info["entry_count"])
    if raw_count <= 0:
        raise ValueError("Singles tree has no accepted entries")

    frame = info["frame"]
    row = {
        "detector_id": int(detector["detector_id"]),
        "source_id": int(source["source_id"]),
        "source_x_mm": float(source["x_mm"]),
        "source_y_mm": float(source["y_mm"]),
        "source_z_mm": float(source["z_mm"]),
        "raw_singles_count": raw_count,
        "ppdf": 1.0,
    }

    # If GATE exported source positions, verify the single configured source;
    # the row itself remains config-driven so no event join is required.
    for column, expected in (
        ("sourcePosX", source["x_mm"]),
        ("sourcePosY", source["y_mm"]),
        ("sourcePosZ", source["z_mm"]),
    ):
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
            if np.isnan(values).any() or not np.allclose(values, float(expected)):
                raise ValueError(f"Singles source position column {column} disagrees with config")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = pd.DataFrame([row])
    output.to_parquet(OUTPUT_DIR / "ppdf.parquet", index=False)
    output.to_csv(OUTPUT_DIR / "ppdf.csv", index=False)
    print(f"PPDF rows: {len(output)}; raw Singles: {raw_count}; ppdf: 1.0")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - stage must fail loudly
        print(f"PPDF generation failed: {error}", file=sys.stderr)
        sys.exit(1)
