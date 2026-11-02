#!/usr/bin/env python3
"""Reduce completed task-level Singles ROOT trees to compact calibration counts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from onecube_imaging.io import file_sha256, load_config, read_csv, root_tree_entries, write_csv, write_runtime_json


def reduce() -> dict:
    config = load_config(PROJECT_ROOT)
    manifest = read_csv(PROJECT_ROOT / "runtime/manifests/response_simulation_manifest.csv")
    reduced = []
    failures = []
    for task in manifest:
        task_id = int(task["task_id"])
        completion_path = PROJECT_ROOT / f"runtime/calibration/completions/task_{task_id:03d}.json"
        singles_path = PROJECT_ROOT / task["singles_root_path"]
        hits_path = PROJECT_ROOT / task["hits_root_path"]
        if not completion_path.is_file():
            failures.append(f"task {task_id}: no completion record")
            continue
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        if completion.get("status") != "completed":
            failures.append(f"task {task_id}: status={completion.get('status')}")
            continue
        try:
            singles_count = root_tree_entries(singles_path)
            hits_count = root_tree_entries(hits_path)
        except Exception as error:
            failures.append(f"task {task_id}: ROOT reduction failed: {error}")
            continue
        if completion.get("singles_sha256") != file_sha256(singles_path):
            failures.append(f"task {task_id}: Singles ROOT hash does not match completion record")
            continue
        if completion.get("hits_sha256") != file_sha256(hits_path):
            failures.append(f"task {task_id}: Hits ROOT hash does not match completion record")
            continue
        if int(completion.get("singles_entries", -1)) != singles_count:
            failures.append(f"task {task_id}: Singles entry count changed since completion")
            continue
        if int(completion.get("hits_entries", -1)) != hits_count:
            failures.append(f"task {task_id}: Hits entry count changed since completion")
            continue
        reduced.append({
            **task,
            "raw_singles_count": singles_count,
            "raw_hits_count": hits_count,
            "completion_path": str(completion_path),
            "singles_sha256": file_sha256(singles_path),
            "hits_sha256": file_sha256(hits_path),
            "activity_Bq": float(task["activity_Bq"]),
            "acquisition_s": float(task["acquisition_s"]),
        })
    if failures:
        raise RuntimeError("Calibration reduction blocked:\n- " + "\n- ".join(failures))
    if len(reduced) != int(config["resources"]["calibration_tasks"]):
        raise RuntimeError(f"Expected {config['resources']['calibration_tasks']} calibration tasks, reduced {len(reduced)}")
    output = PROJECT_ROOT / "runtime/reduced/calibration_counts.csv"
    fields = list(reduced[0].keys()) if reduced else []
    write_csv(output, reduced, fields)
    summary = {
        "stage": "calibration_reduction",
        "task_count": len(reduced),
        "singles_total_raw_counts": sum(row["raw_singles_count"] for row in reduced),
        "hits_total_raw_counts": sum(row["raw_hits_count"] for row in reduced),
        "input_root_files": 2 * len(reduced),
        "reduced_csv": str(output),
        "activity_units": "Bq",
        "exposure_units": "s",
        "response_reduction": "raw Singles entries retained; downstream rate response is n/(activity_Bq*exposure_s) in cps/Bq",
    }
    write_runtime_json(PROJECT_ROOT / "runtime/provenance/calibration_reduction.json", summary)
    return summary


if __name__ == "__main__":
    try:
        print(json.dumps(reduce(), indent=2))
    except Exception as error:
        print(f"Calibration reduction failed: {error}", file=sys.stderr)
        raise SystemExit(1)
