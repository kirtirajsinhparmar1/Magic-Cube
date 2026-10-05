#!/usr/bin/env python3
"""Run one deterministic full-FOV shard: GATE one source at a time, then reduce it."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import uproot

from production_common import (ROOT, config, family_files, full_inputs, load_reduced,
                               task_paths, verify_provenance)


def command(script: str, *args: str) -> list[str]:
    return [sys.executable, str(ROOT / "scripts" / script), *args]


def complete_task(task, fingerprint, detector_ids) -> bool:
    """Return true only when marker, raw family trees, metadata, and vector are valid."""
    try:
        marker, metadata, _, _ = task_paths(task)
        if not marker.is_file() or marker.read_text().strip() != "0":
            return False
        info = json.loads(metadata.read_text())
        if info.get("fingerprint") != fingerprint or info.get("gate_exit_code") != 0:
            return False
        for kind in ("singles", "hits"):
            for _, path in family_files(task, kind):
                with uproot.open(path) as root_file:
                    _ = root_file["tree"].num_entries
        load_reduced(task, fingerprint, detector_ids)
        return True
    except Exception:
        return False


def run_task(task, manifest: Path, fingerprint, detector_ids) -> tuple[str, str | None]:
    task_id = str(int(task.task_id))
    if complete_task(task, fingerprint, detector_ids):
        return "skipped", None
    try:
        subprocess.run(command("record_full_task.py", "--task-id", task_id), check=True)
        subprocess.run(command("render_gate_macro.py", "--manifest", str(manifest),
                              "--task-id", task_id, "--mode", "full"), check=True)
        run_dir = ROOT / "runtime" / "generated_macros" / "full" / f"task_{int(task.task_id):06d}"
        log_path = ROOT / "runtime" / "logs" / "full" / f"gate_{int(task.task_id)}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w") as log:
            gate = subprocess.run(["Gate", "main.mac"], cwd=run_dir, stdout=log,
                                  stderr=subprocess.STDOUT, check=False)
        subprocess.run(command("record_full_task.py", "--task-id", task_id,
                              "--exit-code", str(gate.returncode)), check=True)
        if gate.returncode != 0:
            return "failed", f"GATE exit {gate.returncode}"
        reduced = subprocess.run(command("reduce_source_response.py", "--manifest", str(manifest),
                                         "--task-id", task_id), check=False)
        if reduced.returncode != 0:
            return "failed", f"reduction exit {reduced.returncode}"
        return "completed", None
    except Exception as error:
        try:
            subprocess.run(command("record_full_task.py", "--task-id", task_id,
                                  "--exit-code", "1"), check=False)
        except Exception:
            pass
        return "failed", str(error)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--shard-id", type=int, required=True)
    parser.add_argument("--shards", type=int, required=True)
    args = parser.parse_args()
    if args.shards < 1 or not 0 <= args.shard_id < args.shards:
        raise ValueError("Shard ID must be in [0, shards)")
    _, tasks, mapping = full_inputs(args.manifest)
    fingerprint = verify_provenance()
    detector_ids = mapping.detector_id.to_numpy(dtype=np.int64)
    assigned = tasks[tasks.task_id.map(lambda task_id: int(task_id) % args.shards == args.shard_id)]
    results = {"shard_id": args.shard_id, "shards": args.shards, "task_ids": assigned.task_id.astype(int).tolist(),
               "completed": [], "skipped": [], "failed": {}}
    for _, task in assigned.iterrows():
        status, detail = run_task(task, args.manifest, fingerprint, detector_ids)
        task_id = int(task.task_id)
        if status == "failed":
            results["failed"][str(task_id)] = detail
        else:
            results[status].append(task_id)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 1 if results["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
