#!/usr/bin/env python3
"""Aggregate compact response vectors, preserving raw counts and summed replicate exposure."""
import numpy as np
import pandas as pd

from production_common import (MATRIX, config, full_inputs, load_reduced, verify_provenance,
                               write_json, write_long_parquet)


def main():
    sources, tasks, mapping = full_inputs()
    fingerprint = verify_provenance()
    raw = np.zeros((len(mapping), len(sources)), dtype=np.int64)
    duration = np.zeros(len(sources), dtype=float)
    columns = {int(s): j for j, s in enumerate(sources.source_id)}
    for _, task in tasks.iterrows():
        counts, _ = load_reduced(task, fingerprint, mapping.detector_id.to_numpy())
        j = columns[int(task.source_id)]
        raw[:, j] += counts
        duration[j] += float(task.acquisition_s)
    response = raw / (duration * sources.activity_bq.to_numpy())[None, :]
    MATRIX.mkdir(parents=True, exist_ok=True)
    np.save(MATRIX / 'system_matrix_raw.npy', raw, allow_pickle=False)
    np.save(MATRIX / 'system_matrix.npy', response, allow_pickle=False)
    write_long_parquet(MATRIX / 'system_matrix.parquet', raw, sources, response, 'cps_per_bq', duration)
    write_json(MATRIX / 'system_matrix_metadata.json', {
        'shape': list(raw.shape), 'detector_ids': mapping.detector_id.tolist(), 'source_ids': sources.source_id.tolist(),
        'fingerprint': fingerprint, 'task_ids': tasks.task_id.tolist(), 'raw_total_singles': int(raw.sum()),
        'acquisition_s': duration.tolist(), 'activity_bq': sources.activity_bq.tolist(),
        'raw_file': 'system_matrix_raw.npy', 'normalized_file': 'system_matrix.npy',
        'units': 'counts / second / Bq', 'cps_per_mbq_factor': 1e6,
        'formula': 'n_ij / (sum_replicates(T_j) * A_j)', 'replicates': 'sum counts and live times, do not duplicate source columns',
        'long_format_order': 'source outer, detector inner; each Parquet row group is one source',
        'event_level_global_merge': False})
    sensitivity = response.sum(axis=0) * 1e6
    table = sources[['source_id', 'x_mm', 'y_mm', 'z_mm']].copy()
    table['sensitivity_cps_per_mbq'] = sensitivity
    table['raw_singles_count'] = raw.sum(axis=0)
    table.to_csv(MATRIX / 'sensitivity.csv', index=False)
    table.to_parquet(MATRIX / 'sensitivity.parquet', index=False)
    central = np.flatnonzero((sources.x_mm == 0) & (sources.y_mm == 0))
    target = config('magiccube_config.json')['paper_validation']['reported_average_sensitivity_cps_per_MBq']
    write_json(MATRIX / 'sensitivity_summary.json', {
        'units': 'cps/MBq', 'mean': float(sensitivity.mean()), 'min': float(sensitivity.min()), 'max': float(sensitivity.max()),
        'central': float(sensitivity[central[0]]) if len(central) == 1 else None,
        'paper_target': target, 'mean_relative_difference': float(sensitivity.mean() / target - 1),
        'fov_average': 'unweighted arithmetic mean over configured sampled source positions',
        'endpoint_status': config('source_grid_config.json')['endpoint_status'],
        'scientific_agreement_claimed': False, 'fingerprint': fingerprint})
    print(f'Aggregated {len(tasks)} tasks -> matrix {raw.shape}, {int(raw.sum())} raw Singles')


if __name__ == '__main__':
    main()
