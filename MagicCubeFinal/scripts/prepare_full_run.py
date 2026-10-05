#!/usr/bin/env python3
"""Record immutable production input snapshots and plot-task metadata; no scheduler actions."""
import json
import shutil
from datetime import datetime, timezone

import pandas as pd

from production_common import (ROOT, PROVENANCE, SIM, REDUCED, MATRIX, PPDF, PLOTS,
                               config, current_identity, full_inputs, require, write_json)


def main():
    sources, tasks, mapping = full_inputs()
    prod = config('production_config.json')
    cap = prod['full_array_max_concurrent']
    require(isinstance(cap, int) and cap > 0, 'Concurrency must be a positive integer')
    shards = prod['full_worker_shards']
    require(isinstance(shards, int) and 0 < shards <= len(tasks), 'Worker shard count must be positive and no greater than task count')
    require(isinstance(prod['full_worker_walltime'], str) and prod['full_worker_walltime'], 'Worker walltime must be configured')
    selected = prod['plot_detector_ids']
    ids = mapping.detector_id.tolist() if selected == 'all' else selected
    require(isinstance(ids, list) and ids and len(set(ids)) == len(ids) and all(isinstance(i, int) and i in mapping.detector_id.values for i in ids), 'Invalid plot detector subset')
    identity = current_identity()
    metadata = PROVENANCE / 'run_metadata.json'
    write_record = not metadata.exists()
    if metadata.exists():
        if json.loads(metadata.read_text())['identity'] != identity:
            # Configuration may be adjusted before launch, but not mixed with existing runtime data.
            no_runtime_data = (next(SIM.glob('*.root'), None) is None and
                               next(SIM.glob('task_*.exit_code.txt'), None) is None and
                               next(REDUCED.glob('*.npz'), None) is None)
            require(no_runtime_data, 'Existing production provenance differs and runtime data exist; preserve this run and use a separate run before changing inputs')
            write_record = True
    for directory in (SIM, REDUCED, MATRIX, PPDF, PLOTS, PROVENANCE,
                      ROOT / 'runtime/logs/full', ROOT / 'runtime/generated_macros/full', ROOT / 'results/validation/full'):
        directory.mkdir(parents=True, exist_ok=True)
    for rel in identity['files']:
        target = PROVENANCE / 'inputs' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    pd.DataFrame({'task_id': range(len(ids)), 'detector_id': ids}).to_csv(ROOT / 'runtime/manifests/plot_manifest_full.csv', index=False)
    if write_record:
        write_json(metadata, {'mode': 'full', 'prepared_utc': datetime.now(timezone.utc).isoformat(),
                             'runtime_status': 'NOT_RUN', 'identity': identity,
                             'source_count': len(sources), 'task_count': len(tasks), 'detector_count': len(mapping),
                             'worker_shards': shards, 'worker_walltime': prod['full_worker_walltime'],
                             'ordering': 'y outer, x inner; source table row order defines matrix columns',
                             'raw_root_policy': 'preserved', 'data_flow': 'raw ROOT -> per-source vector -> aggregate matrix'})
    print(f'Prepared {len(sources)} sources, {len(tasks)} simulation/reduction tasks, {len(ids)} plotting tasks')


if __name__ == '__main__':
    main()
