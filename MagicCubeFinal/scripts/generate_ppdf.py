#!/usr/bin/env python3
"""Aggregate raw Singles over replicates and normalize each detector across sources."""
import sys

import numpy as np
import pandas as pd

from inspect_root import PROJECT_ROOT, detector_map, source_manifest, write_json, write_table, stage_arguments


def response_table():
    detectors = detector_map()
    manifest = source_manifest()
    sources = manifest.drop_duplicates('source_id').sort_values('source_id')
    singles = pd.read_csv(PROJECT_ROOT / 'runtime' / 'merged' / 'singles_canonical.csv')
    required = {'detector_id', 'source_id', 'replicate_id', 'task_id'}
    if not required.issubset(singles):
        raise ValueError('Merged Singles lack canonical task/source/replicate/detector context')
    if not singles.detector_id.isin(detectors.detector_id).all() or not singles.source_id.isin(sources.source_id).all():
        raise ValueError('Merged Singles include unknown detector or source IDs')
    contexts = singles[['task_id', 'source_id', 'replicate_id']].drop_duplicates()
    checked = contexts.merge(manifest[['task_id', 'source_id', 'replicate_id']], how='left', indicator=True)
    if (checked['_merge'] != 'both').any():
        raise ValueError('Merged Singles contain a task/source/replicate identity absent from manifest')
    grid = pd.MultiIndex.from_product([detectors.detector_id, sources.source_id], names=['detector_id', 'source_id'])
    counts = singles.groupby(['detector_id', 'source_id']).size().reindex(grid, fill_value=0).astype('int64')
    frame = counts.rename('raw_singles_count').reset_index()
    frame = frame.merge(sources[['source_id', 'source_x_mm', 'source_y_mm', 'source_z_mm', 'activity_bq']], on='source_id', validate='many_to_one')
    exposures = manifest.groupby('source_id').acquisition_s.sum()
    frame['acquisition_s'] = frame.source_id.map(exposures)
    totals = frame.groupby('detector_id').raw_singles_count.transform('sum').to_numpy()
    frame['ppdf'] = np.divide(frame.raw_singles_count, totals, out=np.zeros(len(frame), dtype=float), where=totals != 0)
    return frame, sources


def main():
    stage_arguments(__doc__)
    frame, sources = response_table()
    out = PROJECT_ROOT / 'results' / 'ppdf'
    columns = ['detector_id', 'source_id', 'source_x_mm', 'source_y_mm', 'source_z_mm', 'raw_singles_count', 'ppdf']
    parquet = write_table(frame[columns], out / 'ppdf')
    write_json(out / 'ppdf_metadata.json', {'rows': len(frame), 'source_ids': sources.source_id.astype(int).tolist(),
               'normalization': 'raw_singles_count / sum over sources for each detector',
               'zero_denominator_policy': 'all probabilities zero', 'replicate_policy': 'sum raw counts', 'parquet_written': parquet})
    print(f'PPDF: {len(frame)} rows, {int(frame.raw_singles_count.sum())} raw Singles')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'PPDF generation failed: {error}', file=sys.stderr)
        sys.exit(1)
