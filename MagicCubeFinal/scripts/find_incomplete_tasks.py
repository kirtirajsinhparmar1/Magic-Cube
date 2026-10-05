#!/usr/bin/env python3
"""Read-only resume diagnostics. Prints task IDs/array ranges; never submits jobs or retries."""
import json

from production_common import (full_inputs, task_paths, family_files, verify_provenance,
                               load_reduced, config)


def array_spec(ids):
    groups = []
    for task in sorted(ids):
        if groups and task == groups[-1][-1] + 1:
            groups[-1].append(task)
        else:
            groups.append([task])
    return ','.join(str(g[0]) if len(g) == 1 else f'{g[0]}-{g[-1]}' for g in groups)


def main():
    _, tasks, mapping = full_inputs()
    fingerprint = verify_provenance()
    complete, missing, failed, simulation_incomplete, reduction_incomplete = [], [], [], [], []
    details = {}
    for _, task in tasks.iterrows():
        tid = int(task.task_id)
        marker, metadata, vector, summary = task_paths(task)
        try:
            if not marker.is_file():
                missing.append(tid)
                simulation_incomplete.append(tid)
                details[tid] = 'exit marker missing'
                continue
            state = marker.read_text().strip()
            if state != '0':
                (missing if state == 'RUNNING' else failed).append(tid)
                simulation_incomplete.append(tid)
                details[tid] = f'GATE state {state}'
                continue
            gate = json.loads(metadata.read_text())
            if gate['fingerprint'] != fingerprint or gate['seed'] != int(task.seed) or gate['gate_exit_code'] != 0:
                raise ValueError('simulation metadata incompatible')
            for kind in ('hits', 'singles'):
                for _, path in family_files(task, kind):
                    if path.stat().st_size == 0:
                        raise ValueError(f'empty {path.name}')
        except Exception as exc:
            failed.append(tid)
            simulation_incomplete.append(tid)
            details[tid] = str(exc)
            continue
        if not vector.is_file() or not summary.is_file():
            missing.append(tid)
            reduction_incomplete.append(tid)
            details[tid] = 'reduction missing; reuse successful ROOT outputs'
            continue
        try:
            load_reduced(task, fingerprint, mapping.detector_id.to_numpy())
            complete.append(tid)
        except Exception as exc:
            failed.append(tid)
            reduction_incomplete.append(tid)
            details[tid] = str(exc)
    print(json.dumps({'complete_task_ids': complete, 'missing_task_ids': missing, 'failed_task_ids': failed,
          'simulation_incomplete_array': array_spec(simulation_incomplete),
          'reduction_incomplete_array': array_spec(reduction_incomplete), 'details': details,
          'incomplete_shard_ids': sorted({tid % config('production_config.json')['full_worker_shards']
                                         for tid in simulation_incomplete + reduction_incomplete}),
          'automatic_resubmission': False}, indent=2))


if __name__ == '__main__':
    main()
