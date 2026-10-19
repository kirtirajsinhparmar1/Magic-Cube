#!/usr/bin/env python3
"""Generate the OneCube long-form and dense 1x1 system matrix products."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from inspect_root import load_config, read_tree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SINGLES_PATH = PROJECT_ROOT / "runtime" / "merged" / "singles.root"
OUTPUT_DIR = PROJECT_ROOT / "results" / "system_matrix"


def main() -> int:
    config = load_config()
    detector = config["detector"]
    source = config["source"]
    acquisition = config["acquisition"]
    output = config["output"]

    if int(detector["count"]) != 1 or int(source["source_count"]) != 1:
        raise ValueError("OneCube system matrix requires exactly one detector and one source")
    if output["detector_ids"] != [int(detector["detector_id"])]:
        raise ValueError("Configured detector identity is inconsistent")

    singles = read_tree(SINGLES_PATH)
    raw_count = int(singles["entry_count"])
    if raw_count <= 0:
        raise ValueError("Singles tree has no accepted entries")

    duration_s = float(acquisition["duration_s"])
    activity_bq = float(source["activity_Bq"])
    if duration_s <= 0 or activity_bq <= 0:
        raise ValueError("Acquisition duration and source activity must be positive")

    response_per_bq_s = raw_count / (duration_s * activity_bq)
    response_cps_per_mbq = response_per_bq_s * 1.0e6
    if not np.isfinite(response_per_bq_s) or response_per_bq_s < 0:
        raise ValueError("Normalized response is not finite and non-negative")

    row = {
        "detector_id": int(detector["detector_id"]),
        "source_id": int(source["source_id"]),
        "source_x_mm": float(source["x_mm"]),
        "source_y_mm": float(source["y_mm"]),
        "source_z_mm": float(source["z_mm"]),
        "raw_singles_count": raw_count,
        "activity_Bq": activity_bq,
        "acquisition_s": duration_s,
        "response_per_Bq_s": response_per_bq_s,
        "response_cps_per_MBq": response_cps_per_mbq,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    long_form = pd.DataFrame([row])
    long_form.to_parquet(OUTPUT_DIR / "system_matrix.parquet", index=False)
    long_form.to_csv(OUTPUT_DIR / "system_matrix.csv", index=False)

    matrix = np.asarray([[response_per_bq_s]], dtype=np.float64)
    if matrix.shape != (1, 1):
        raise ValueError(f"Dense matrix has unexpected shape {matrix.shape}")
    np.save(OUTPUT_DIR / "system_matrix.npy", matrix)

    metadata = {
        "shape": [1, 1],
        "npy_quantity": "response_per_Bq_s",
        "npy_units": "counts / (s * Bq), numerically cps/Bq",
        "normalization": "raw_singles_count / (acquisition_s * activity_Bq)",
        "raw_count_preserved": True,
        "detector_ids": [int(detector["detector_id"])],
        "source_ids": [int(source["source_id"])],
        "activity_Bq": activity_bq,
        "acquisition_s": duration_s,
    }
    with (OUTPUT_DIR / "system_matrix_metadata.json").open("w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
        stream.write("\n")

    print(f"System matrix shape: {matrix.shape}; raw Singles: {raw_count}; cps/MBq: {response_cps_per_mbq}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - stage must fail loudly
        print(f"System-matrix generation failed: {error}", file=sys.stderr)
        sys.exit(1)
