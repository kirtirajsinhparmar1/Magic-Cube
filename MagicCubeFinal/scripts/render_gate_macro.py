#!/usr/bin/env python3
"""Stage a standalone task macro set. Run GATE with the task directory as cwd."""
import argparse
import csv
import json
import math
import os
import re
import shutil
from pathlib import Path
from generate_detector_map import validate_config

BASE = Path(__file__).resolve().parents[1]


def number(value, positive=False):
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError("Macro numbers must be finite; time and activity must be positive")
    return format(value, ".12g")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=BASE / "runtime/manifests/simulation_manifest_validation.csv")
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--mode", choices=["validation", "full"], default="validation")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output-prefix", help="Optional task-relative path without spaces or macro control characters")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--config", type=Path, default=BASE / "config/magiccube_config.json")
    args = parser.parse_args()
    if args.task_id < 0:
        raise ValueError("Task ID must be nonnegative")
    with args.manifest.open(newline="") as handle:
        tasks = [row for row in csv.DictReader(handle) if int(row["task_id"]) == args.task_id]
    if len(tasks) != 1:
        raise ValueError(f"Task {args.task_id} must occur exactly once in manifest")
    task = tasks[0]
    config = json.loads(args.config.read_text())
    validate_config(config)
    source = config["source"]
    if (source["particle"], source["type"], source["angular_distribution"]) != ("gamma", "Point", "iso"):
        raise ValueError("Frozen source model requires an isotropic gamma Point source")
    if config["physics"] != {"process": "PhotoElectric", "model": "StandardModel", "production_cut_cm": 1.0}:
        raise ValueError("Frozen physics differs from the macro contract")
    expected_digitizer = {"modules": ["adder", "energyResolution", "spatialResolution", "energyFraming"], "energy_resolution_fwhm": 0.10, "reference_energy_keV": 140.0, "spatial_resolution_fwhm_mm": 1.0, "confine_inside_smallest_element": True, "energy_window_keV": [120.0, 160.0]}
    if config["digitizer"] != expected_digitizer:
        raise ValueError("Frozen digitizer differs from the macro contract")
    generated = BASE / "runtime/generated_macros"
    if args.mode == "full":
        generated = generated / "full"
    run_dir = (args.run_dir or generated / f"task_{args.task_id:06d}").resolve()
    templates = BASE / "GATE-Macro"
    if run_dir == templates.resolve() or templates.resolve() in run_dir.parents:
        raise ValueError("Run directory cannot overwrite source macro templates")
    if args.output_prefix is None:
        output_target = BASE / "runtime/sim" / f"source_{int(task['source_id']):04d}_rep_{int(task['replicate_id']):03d}"
        if args.mode == "full":
            output_target = BASE / "runtime/sim/full" / output_target.name
        output_prefix = os.path.relpath(output_target, run_dir)
    else:
        output_prefix = args.output_prefix
        prefix = Path(output_prefix)
        if prefix.is_absolute() or ".." in prefix.parts:
            raise ValueError("Explicit output prefix must be a safe task-relative path")
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", output_prefix):
        raise ValueError("Output prefix cannot contain spaces or macro control characters")
    prefix = Path(output_prefix)
    seed = args.seed if args.seed is not None else int(task.get("seed", 1000001 + args.task_id))
    if seed < 1 or seed > 2147483647:
        raise ValueError("Seed must fit a positive signed 32-bit integer")
    replacements = {
        "MACRO_DIR": ".", "RUN_DIR": ".", "SEED": str(seed),
        "OUTPUT_PREFIX": output_prefix,
        "ENERGY_KEV": number(source["energy_keV"], True),
        "ACTIVITY_BQ": number(task.get("activity_bq", task.get("activity_Bq")), True),
        "ACQUISITION_TIME_S": number(task.get("acquisition_s", task.get("acquisition_time_s")), True),
        **{axis.upper() + "_MM": number(task[axis + "_mm"]) for axis in ("x", "y", "z")},
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / prefix).parent.mkdir(parents=True, exist_ok=True)
    for path in sorted(templates.iterdir()):
        if path.suffix != ".mac" and path.name != "GateMaterials.db":
            continue
        content = path.read_text()
        for key, value in replacements.items():
            content = content.replace("@" + key + "@", value)
        if re.search(r"@[A-Z_]+@", content):
            raise ValueError(f"Unresolved macro token in {path.name}")
        (run_dir / path.name).write_text(content)
    metadata = {"task": task, "seed": seed, "config": str(args.config.resolve()), "run_directory": str(run_dir), "output_prefix": output_prefix, "cwd_required": str(run_dir)}
    (run_dir / "task_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    generated.mkdir(parents=True, exist_ok=True)
    entry = generated / f"task_{args.task_id:06d}.mac"
    shutil.copyfile(run_dir / "main.mac", entry)
    print(entry)
    print(f"Run from {run_dir}: Gate main.mac")


if __name__ == "__main__":
    main()
