#!/usr/bin/env python3
"""Reduce one full-mode source/replicate's four Singles trees to a dense detector vector."""
import argparse
import json

import numpy as np
import pandas as pd
import uproot

from inspect_root import map_positions, validate_source_positions
from production_common import (config, full_inputs, task_paths, family_files, verify_provenance,
                               prefix, require, sha256, write_json)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-id', type=int, required=True)
    parser.add_argument('--manifest', type=str)
    args = parser.parse_args()
    kwargs = {'manifest': args.manifest} if args.manifest else {}
    _, tasks, mapping = full_inputs(**kwargs)
    selection = tasks.loc[tasks.task_id == args.task_id]
    require(len(selection) == 1, 'Task must occur exactly once')
    task = selection.iloc[0]
    marker, task_meta, vector_path, metadata_path = task_paths(task)
    require(marker.read_text().strip() == '0', f'Task {args.task_id}: GATE exit is not successful')
    fingerprint = verify_provenance()
    gate_meta = json.loads(task_meta.read_text())
    require(gate_meta['fingerprint'] == fingerprint and gate_meta['seed'] == int(task.seed) and gate_meta['gate_exit_code'] == 0, 'Simulation provenance mismatch')
    counts = np.zeros(len(mapping), dtype=np.int64)
    family_counts, hits_counts, inputs = {}, {}, []
    for family, path in family_files(task, 'singles'):
        observed = 0
        with uproot.open(path) as root:
            tree = root['tree']
            for arrays in tree.iterate(step_size=config('production_config.json')['root_step_size'], library='np'):
                if isinstance(arrays, np.ndarray) and arrays.dtype.names:
                    arrays = {key: arrays[key] for key in arrays.dtype.names}
                frame = pd.DataFrame({key: value for key, value in arrays.items() if np.asarray(value).ndim == 1})
                require(len(frame) == len(next(iter(arrays.values()))), 'ROOT entries not preserved')
                frame['gagg_family'] = family
                validate_source_positions(frame, task)
                ids = map_positions(frame, 'singles')
                require(np.all(mapping.iloc[ids].family.to_numpy() == family), 'Position-derived detector family disagrees with ROOT shard')
                counts += np.bincount(ids, minlength=len(mapping))
                observed += len(frame)
            require(observed == tree.num_entries, 'Singles entry conservation failed')
        family_counts[family] = observed
        inputs.append({'family': family, 'kind': 'singles', 'path': str(path), 'entries': observed, 'bytes': path.stat().st_size})
    for family, path in family_files(task, 'hits'):
        with uproot.open(path) as root:
            entries = int(root['tree'].num_entries)
        hits_counts[family] = entries
        inputs.append({'family': family, 'kind': 'hits', 'path': str(path), 'entries': entries, 'bytes': path.stat().st_size})
    require(int(counts.sum()) == sum(family_counts.values()), 'Raw Singles count was lost')
    vector_path.parent.mkdir(parents=True, exist_ok=True)
    scalars = {name: task[name] for name in ('task_id', 'source_id', 'replicate_id', 'seed', 'activity_bq', 'acquisition_s', 'source_x_mm', 'source_y_mm', 'source_z_mm')}
    np.savez_compressed(vector_path, detector_id=mapping.detector_id.to_numpy(dtype=np.int64), raw_singles_count=counts, **scalars)
    write_json(metadata_path, {**scalars, 'fingerprint': fingerprint, 'npz_sha256': sha256(vector_path),
                              'detector_rows': len(mapping), 'raw_total_singles': int(counts.sum()),
                              'singles_by_family': family_counts, 'hits_by_family': hits_counts,
                              'inputs': inputs, 'mapping': 'validated position-derived unique cube containment',
                              'raw_root_preserved': True})
    print(f'{prefix(task)}: {int(counts.sum())} Singles -> {len(mapping)} detector rows')


if __name__ == '__main__':
    main()
