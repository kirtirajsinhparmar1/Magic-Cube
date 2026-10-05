#!/usr/bin/env python3
"""Record task launch/exit metadata and invalidate stale success markers before a rerun."""
import argparse
from datetime import datetime, timezone

from production_common import full_inputs, task_paths, verify_provenance, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-id', type=int, required=True)
    parser.add_argument('--exit-code', type=int)
    args = parser.parse_args()
    _, tasks, _ = full_inputs()
    task = tasks.loc[tasks.task_id == args.task_id].iloc[0]
    marker, metadata, _, _ = task_paths(task)
    fingerprint = verify_provenance()
    values = task.to_dict()
    values.update(fingerprint=fingerprint, status='RUNNING' if args.exit_code is None else ('COMPLETED' if args.exit_code == 0 else 'FAILED'),
                  gate_exit_code=args.exit_code, recorded_utc=datetime.now(timezone.utc).isoformat())
    write_json(metadata, values)
    marker.write_text('RUNNING\n' if args.exit_code is None else f'{args.exit_code}\n')


if __name__ == '__main__':
    main()
