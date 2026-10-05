#!/usr/bin/env python3
"""Generate the validation source or an explicitly selected source grid."""
import argparse
import csv
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
COLUMNS = ["source_id", "ix", "iy", "x_mm", "y_mm", "z_mm", "activity_Bq", "acquisition_time_s",
           "particle", "energy_keV", "source_model", "angular_distribution", "reported_nominal_source_size_mm"]


def grid_axis(fov, spacing, center, mode):
    if not all(math.isfinite(value) for value in (fov, spacing, center)) or fov <= 0 or spacing <= 0:
        raise ValueError("FOV and spacing must be finite and positive")
    intervals = round(fov / spacing)
    if not math.isclose(intervals * spacing, fov, abs_tol=1e-9):
        raise ValueError("FOV must be an integer multiple of grid spacing")
    if mode in ("inclusive", "centered_inclusive"):
        count, start = intervals + 1, center - fov / 2
    elif mode == "voxel_centers":
        count, start = intervals, center - fov / 2 + spacing / 2
    else:
        raise ValueError("Endpoint mode unresolved: explicitly choose inclusive or voxel_centers")
    return [round(start + index * spacing, 9) for index in range(count)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["validation", "full", "grid"], default="validation")
    parser.add_argument("--config", type=Path, default=BASE / "config/magiccube_config.json")
    parser.add_argument("--grid-config", type=Path, default=BASE / "config/source_grid_config.json")
    parser.add_argument("--endpoint-mode", choices=["centered_inclusive", "inclusive", "voxel_centers"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.config.read_text())["source"]
    if args.mode == "validation":
        x, y, z = source["validation_position_mm"]
        rows = [dict(zip(COLUMNS, [source["validation_source_id"], 0, 0, x, y, z, source["activity_Bq"], source["acquisition_time_s"],
                                  source["particle"], source["energy_keV"], source["type"], "isotropic", 0.7]))]
    else:
        grid = json.loads(args.grid_config.read_text())
        mode = args.endpoint_mode or grid["endpoint_mode"]
        axes = {axis: grid_axis(grid[f"fov_{axis}_mm"], grid[f"spacing_{axis}_mm"], grid["center_mm"][axis], mode) for axis in ("x", "y")}
        rows = [dict(zip(COLUMNS, [grid["source_id_start"] + iy * len(axes["x"]) + ix, ix, iy, x, y, grid["z_mm"], grid["activity_Bq"], grid["acquisition_time_s"],
                                  grid["particle"], grid["energy_keV"], grid["source_model"], grid["angular_distribution"], grid["reported_nominal_source_size_mm"]]))
                for iy, y in enumerate(axes["y"]) for ix, x in enumerate(axes["x"])]
    output = args.output or (BASE / "config/validation_source_positions.csv" if args.mode == "validation" else BASE / "config/full_source_positions.csv")
    columns = list(COLUMNS)
    if args.mode != "validation":
        columns += ["activity_bq", "acquisition_s"]
        for row in rows:
            row.update(activity_bq=grid["activity_bq"], acquisition_s=grid["acquisition_s"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    if args.mode != "validation":
        import pandas as pd
        pd.DataFrame(rows, columns=columns).to_parquet(output.with_suffix(".parquet"), index=False)
    print(f"Wrote {len(rows)} sources to {output}")


if __name__ == "__main__":
    main()
