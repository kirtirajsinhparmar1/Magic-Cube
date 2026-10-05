#!/usr/bin/env python3
"""Create one deterministic task per source/replicate, with explicit normalization."""
import argparse
import csv
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
COLUMNS = ["task_id", "source_id", "replicate_id", "x_mm", "y_mm", "z_mm", "activity_bq", "acquisition_s", "seed", "expected_emitted_photons"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["validation", "full"], default="validation")
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replicates", type=int)
    parser.add_argument("--seed-base", type=int)
    args = parser.parse_args()
    grid = json.loads((BASE / "config/source_grid_config.json").read_text())
    production = json.loads((BASE / "config/production_config.json").read_text())
    args.replicates = args.replicates if args.replicates is not None else (grid["replicates_per_source"] if args.mode == "full" else 1)
    args.seed_base = args.seed_base if args.seed_base is not None else production["seed_base"]
    if args.replicates < 1 or args.seed_base < 1:
        raise ValueError("Replicates and seed base must be positive")
    source_path = args.sources or (BASE / "config/validation_source_positions.csv" if args.mode == "validation" else BASE / "config/full_source_positions.csv")
    with source_path.open(newline="") as handle:
        sources = list(csv.DictReader(handle))
    if not sources or len({row["source_id"] for row in sources}) != len(sources):
        raise ValueError("Source IDs must be unique and source table must not be empty")
    rows = []
    for source in sources:
        activity_key = "activity_bq" if "activity_bq" in source else "activity_Bq"
        duration_key = "acquisition_s" if "acquisition_s" in source else "acquisition_time_s"
        for key in ("x_mm", "y_mm", "z_mm", activity_key, duration_key):
            if not math.isfinite(float(source[key])):
                raise ValueError(f"Non-finite source field {key}")
        activity, duration = float(source[activity_key]), float(source[duration_key])
        if activity <= 0 or duration <= 0:
            raise ValueError("Source activity and duration must be positive")
        for replicate in range(args.replicates):
            task = len(rows)
            rows.append({"task_id": task, "source_id": int(source["source_id"]), "replicate_id": replicate, **{key: source[key] for key in ("x_mm", "y_mm", "z_mm")}, "activity_bq": activity, "acquisition_s": duration, "seed": args.seed_base + task, "expected_emitted_photons": activity * duration})
    output = args.output or BASE / "runtime/manifests" / f"simulation_manifest_{args.mode}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} tasks to {output}")


if __name__ == "__main__":
    main()
