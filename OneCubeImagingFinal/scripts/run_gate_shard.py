#!/usr/bin/env python3
"""Run assigned OneCube Gate tasks with task-level provenance and resume support."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from onecube_imaging.io import file_sha256, load_config, read_csv, root_tree_entries, write_runtime_json


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _output_paths(project_root: Path, task: dict[str, str]) -> tuple[Path, Path, Path]:
    return tuple(project_root / task[key] for key in (
        "root_base_path", "singles_root_path", "hits_root_path"
    ))  # type: ignore[return-value]


def _completion_is_valid(
    completion_path: Path, macro_path: Path, singles_path: Path, hits_path: Path
) -> bool:
    if not all(path.is_file() for path in (completion_path, macro_path, singles_path, hits_path)):
        return False
    try:
        record = json.loads(completion_path.read_text(encoding="utf-8"))
        return (
            record.get("status") == "completed"
            and record.get("macro_sha256") == file_sha256(macro_path)
            and record.get("singles_sha256") == file_sha256(singles_path)
            and record.get("hits_sha256") == file_sha256(hits_path)
        )
    except (OSError, ValueError, KeyError):
        return False


def _quarantine(paths: tuple[Path, ...], quarantine_dir: Path, task_key: str) -> None:
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    for path in paths:
        if path.exists():
            destination = quarantine_dir / f"{task_key}_{stamp}_{path.name}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))


def _run_task(
    stage: str,
    task: dict[str, str],
    config: dict,
    gate_executable: str,
    shard_index: int,
) -> tuple[bool, str]:
    task_id = int(task["task_id"])
    task_key = f"{stage}_{task_id:03d}"
    macro_path = PROJECT_ROOT / task["macro_path"]
    completion_path = PROJECT_ROOT / "runtime" / stage / "completions" / f"task_{task_id:03d}.json"
    root_base, singles_path, hits_path = _output_paths(PROJECT_ROOT, task)
    if _completion_is_valid(completion_path, macro_path, singles_path, hits_path):
        return True, f"{task_key}: already complete; ROOT hashes verified"
    if not macro_path.is_file():
        write_runtime_json(completion_path, {
            "task_key": task_key, "status": "failed", "failure": f"missing task macro: {macro_path}",
            "shard_index": shard_index, "finished_utc": _utc_now(),
        })
        return False, f"{task_key}: missing macro {macro_path}"

    _quarantine(
        (root_base, singles_path, hits_path, completion_path),
        PROJECT_ROOT / "runtime" / "quarantine",
        task_key,
    )
    root_base.parent.mkdir(parents=True, exist_ok=True)
    log_path = PROJECT_ROOT / "runtime" / "logs" / f"{task_key}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = _utc_now()
    start_clock = time.monotonic()
    command = [gate_executable, str(macro_path)]
    try:
        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"Started UTC: {started}\nCommand: {command!r}\n")
            log.flush()
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT / config["baseline_project_relative"] / config["baseline"]["gate_working_directory"],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        duration = time.monotonic() - start_clock
        if completed.returncode != 0:
            raise RuntimeError(f"Gate exited with status {completed.returncode}")
        singles_count = root_tree_entries(singles_path)
        hits_count = root_tree_entries(hits_path)
        record = {
            "task_key": task_key,
            "stage": stage,
            "task_id": task_id,
            "condition_id": task.get("condition_id"),
            "pose_id": task.get("pose_id"),
            "row_id": task.get("row_id"),
            "detector_id": int(task["detector_id"]),
            "source_x_mm": task.get("source_x_mm"),
            "source_y_mm": task.get("source_y_mm"),
            "source_z_mm": task.get("source_z_mm"),
            "detector_x_mm": task.get("detector_x_mm"),
            "detector_y_mm": task.get("detector_y_mm"),
            "detector_z_mm": task.get("detector_z_mm"),
            "activity_Bq": task.get("activity_Bq", task.get("activity_total_Bq")),
            "exposure_s": task.get("acquisition_s"),
            "seed": int(task["seed"]),
            "gate_exit_status": completed.returncode,
            "status": "completed",
            "started_utc": started,
            "finished_utc": _utc_now(),
            "elapsed_seconds": duration,
            "macro_path": str(macro_path),
            "macro_sha256": file_sha256(macro_path),
            "root_base_path": str(root_base),
            "singles_root_path": str(singles_path),
            "singles_sha256": file_sha256(singles_path),
            "singles_entries": singles_count,
            "hits_root_path": str(hits_path),
            "hits_sha256": file_sha256(hits_path),
            "hits_entries": hits_count,
            "log_path": str(log_path),
        }
        write_runtime_json(completion_path, record)
        return True, f"{task_key}: completed; Singles={singles_count}, Hits={hits_count}, {duration:.1f}s"
    except Exception as error:
        write_runtime_json(completion_path, {
            "task_key": task_key,
            "stage": stage,
            "task_id": task_id,
            "seed": int(task["seed"]),
            "gate_exit_status": getattr(locals().get("completed"), "returncode", None),
            "status": "failed",
            "failure": str(error),
            "started_utc": started,
            "finished_utc": _utc_now(),
            "macro_path": str(macro_path),
            "log_path": str(log_path),
            "root_base_path": str(root_base),
            "singles_root_path": str(singles_path),
            "hits_root_path": str(hits_path),
        })
        return False, f"{task_key}: FAILED: {error}; see {log_path}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("calibration", "phantom"), required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, required=True)
    args = parser.parse_args()
    config = load_config(PROJECT_ROOT)
    gate = shutil.which("Gate")
    if not gate:
        print("Preflight failed: Gate is not available in PATH; no tasks were started.", file=sys.stderr)
        return 2
    if args.shard_count != int(config["resources"]["gate_workers"]):
        print("Shard count differs from configured worker count.", file=sys.stderr)
        return 2
    if not 0 <= args.shard_index < args.shard_count:
        print("Shard index must be within [0, shard_count).", file=sys.stderr)
        return 2
    manifest_name = (
        "response_simulation_manifest.csv" if args.stage == "calibration"
        else "phantom_acquisition_manifest.csv"
    )
    tasks = read_csv(PROJECT_ROOT / "runtime" / "manifests" / manifest_name)
    assigned = [task for task in tasks if int(task["task_id"]) % args.shard_count == args.shard_index]
    print(f"Gate preflight OK: {gate}; stage={args.stage}; shard={args.shard_index}/{args.shard_count}; tasks={len(assigned)}")
    failures = []
    for task in assigned:
        success, message = _run_task(args.stage, task, config, gate, args.shard_index)
        print(message, flush=True)
        if not success:
            failures.append(message)
    if failures:
        print(f"{len(failures)} task(s) failed; no automatic retries were attempted.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
