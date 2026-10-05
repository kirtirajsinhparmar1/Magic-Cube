#!/usr/bin/env python3
"""Validate compact production artifacts against every source/task and its raw ROOT shards."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import uproot

from production_common import (ROOT, MANIFEST, MATRIX, PPDF, PLOTS, config, full_inputs,
                               family_files, load_reduced, task_paths, verify_provenance, write_json)


def validate(manifest=None):
    failures, checks = [], {}

    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            failures.append(name)

    try:
        sources, tasks, mapping = full_inputs(Path(manifest) if manifest else MANIFEST)
        fingerprint = verify_provenance()
        shape = (len(mapping), len(sources))
        check('source_grid_and_manifest', True)
        check('provenance_copies_and_checksums', True)
        raw = np.load(MATRIX / 'system_matrix_raw.npy', mmap_mode='r', allow_pickle=False)
        response = np.load(MATRIX / 'system_matrix.npy', mmap_mode='r', allow_pickle=False)
        ppdf = np.load(PPDF / 'ppdf.npy', mmap_mode='r', allow_pickle=False)
        check('matrix_shape', raw.shape == response.shape == ppdf.shape == shape)
        if not checks['matrix_shape']:
            raise ValueError('Matrix dimensions prevent further elementwise validation')
        check('nonnegative_raw_integer_counts', np.issubdtype(raw.dtype, np.integer) and (raw >= 0).all())
        check('finite_nonnegative_absolute_response', np.isfinite(response).all() and (response >= 0).all())
        expected = np.zeros(shape, dtype=np.int64)
        duration = np.zeros(len(sources), dtype=float)
        columns = {int(s): j for j, s in enumerate(sources.source_id)}
        total_hits = 0
        for _, task in tasks.iterrows():
            task_id = int(task.task_id)
            label = f'task_{task_id}'
            try:
                marker, task_metadata, _, _ = task_paths(task)
                check(f'{label}_gate_exit', marker.read_text().strip() == '0')
                info = json.loads(task_metadata.read_text())
                check(f'{label}_metadata', info['fingerprint'] == fingerprint and info['gate_exit_code'] == 0 and
                      all(info[name] == task[name] for name in ('task_id', 'source_id', 'replicate_id', 'seed', 'x_mm', 'y_mm', 'z_mm', 'activity_bq', 'acquisition_s')))
                gate_log = ROOT / f'runtime/logs/full/gate_{task_id}.log'
                check(f'{label}_no_fatal_gate_error', gate_log.is_file() and not re.search(r'G4Exception.*Fatal|Fatal Exception|Segmentation fault', gate_log.read_text(errors='replace')))
                root_counts = {}
                for kind in ('singles', 'hits'):
                    root_counts[kind] = {}
                    for family, path in family_files(task, kind):
                        with uproot.open(path) as root:
                            tree = root['tree']
                            root_counts[kind][family] = int(tree.num_entries)
                            check(f'{label}_{kind}_{family}_readable', hasattr(tree, 'arrays'))
                counts, meta = load_reduced(task, fingerprint, mapping.detector_id.to_numpy())
                check(f'{label}_reduction_count_conservation', meta['singles_by_family'] == root_counts['singles'] and
                      meta['hits_by_family'] == root_counts['hits'] and int(counts.sum()) == sum(root_counts['singles'].values()))
                total_hits += sum(root_counts['hits'].values())
                j = columns[int(task.source_id)]
                expected[:, j] += counts
                duration[j] += float(task.acquisition_s)
            except Exception as error:
                failures.append(f'{label}: {error}')
        check('all_task_vectors_aggregated', np.array_equal(raw, expected))
        check('all_source_exposures_present', (duration > 0).all())
        expected_response = np.divide(expected, duration[None, :] * sources.activity_bq.to_numpy()[None, :],
                                      out=np.zeros(shape, dtype=float), where=duration[None, :] > 0)
        check('absolute_response_formula', np.allclose(response, expected_response, rtol=1e-12, atol=1e-15))
        matrix_meta = json.loads((MATRIX / 'system_matrix_metadata.json').read_text())
        check('matrix_metadata_order_and_identity', matrix_meta['shape'] == list(shape) and
              matrix_meta['detector_ids'] == mapping.detector_id.tolist() and matrix_meta['source_ids'] == sources.source_id.tolist() and
              matrix_meta['task_ids'] == tasks.task_id.tolist() and matrix_meta['fingerprint'] == fingerprint)
        check('matrix_count_and_exposure_metadata', matrix_meta['raw_total_singles'] == int(raw.sum()) and
              np.array_equal(matrix_meta['acquisition_s'], duration) and np.array_equal(matrix_meta['activity_bq'], sources.activity_bq))
        totals = raw.sum(axis=1)
        expected_ppdf = np.divide(raw, totals[:, None], out=np.zeros(shape, dtype=float), where=totals[:, None] > 0)
        check('ppdf_finite_and_formula', np.isfinite(ppdf).all() and np.allclose(ppdf, expected_ppdf, rtol=1e-12, atol=1e-15))
        check('ppdf_row_normalization', np.allclose(ppdf[totals > 0].sum(axis=1), 1.0) and (ppdf[totals == 0] == 0).all())
        ppdf_meta = json.loads((PPDF / 'ppdf_metadata.json').read_text())
        check('ppdf_metadata_order_and_identity', ppdf_meta['shape'] == list(shape) and ppdf_meta['fingerprint'] == fingerprint and
              ppdf_meta['detector_ids'] == mapping.detector_id.tolist() and ppdf_meta['source_ids'] == sources.source_id.tolist() and
              ppdf_meta['zero_response_detector_ids'] == mapping.detector_id[totals == 0].tolist())

        for kind, path, values in (('matrix', MATRIX / 'system_matrix.parquet', response), ('ppdf', PPDF / 'ppdf.parquet', ppdf)):
            parquet = pq.ParquetFile(path)
            check(f'{kind}_parquet_size', parquet.metadata.num_rows == shape[0] * shape[1] and parquet.num_row_groups == len(sources))
            for j, source in sources.iterrows():
                frame = parquet.read_row_group(j).to_pandas()
                valid = len(frame) == len(mapping) and np.array_equal(frame.detector_id, mapping.detector_id) and np.all(frame.source_id == source.source_id)
                valid = valid and np.array_equal(frame.raw_singles_count, raw[:, j])
                valid = valid and all(np.all(frame[f'source_{a}_mm'] == source[f'{a}_mm']) for a in 'xyz')
                field = 'cps_per_bq' if kind == 'matrix' else 'ppdf'
                valid = valid and np.allclose(frame[field], values[:, j], rtol=1e-12, atol=1e-15)
                if kind == 'matrix':
                    valid = valid and np.all(frame.acquisition_s == duration[j]) and np.all(frame.activity_bq == source.activity_bq)
                    valid = valid and np.allclose(frame.cps_per_mbq, response[:, j] * 1e6)
                check(f'{kind}_parquet_source_{int(source.source_id)}', valid)
        sensitivity = pd.read_csv(MATRIX / 'sensitivity.csv')
        check('sensitivity_source_order_and_values', np.array_equal(sensitivity.source_id, sources.source_id) and
              np.allclose(sensitivity.sensitivity_cps_per_mbq, response.sum(axis=0) * 1e6))
        summary = json.loads((MATRIX / 'sensitivity_summary.json').read_text())
        check('sensitivity_summary', summary['fingerprint'] == fingerprint and np.isclose(summary['mean'], sensitivity.sensitivity_cps_per_mbq.mean()) and
              summary['paper_target'] == config('magiccube_config.json')['paper_validation']['reported_average_sensitivity_cps_per_MBq'])
        for name in ('positions.png', 'system_matrix_heatmap.png', 'detector_geometry.png', 'detector_id_layout.png', 'source_grid.png', 'sensitivity_map.png', 'detector_response_summary.png'):
            path = PLOTS / name
            check(f'plot_{name}', path.is_file() and path.stat().st_size > 0)
        plot_manifest = pd.read_csv(ROOT / 'runtime/manifests/plot_manifest_full.csv')
        ids = config('production_config.json')['plot_detector_ids']
        expected_ids = mapping.detector_id.tolist() if ids == 'all' else ids
        check('plot_selection_matches_config', np.array_equal(plot_manifest.detector_id, expected_ids))
        for detector_id in plot_manifest.detector_id:
            path = PLOTS / f'PPDF_Detector_{int(detector_id)}.png'
            check(f'heatmap_{int(detector_id)}', path.is_file() and path.stat().st_size > 0)
        check('all_detector_heatmap_architecture_available', (ROOT / 'slurm/magiccube_heatmap.slurm').is_file())
        check('raw_roots_retained', total_hits >= 0)
    except Exception as error:
        failures.append(f'Full runtime validation could not complete: {error}')
    token = 'MAGICCUBE_FULL_MATRIX_PASS'
    write_json(ROOT / 'results/validation/full/runtime_validation.json', {
        'mode': 'full', 'checks': checks, 'failures': failures, 'passed': not failures,
        'pass_token': token if not failures else None})
    if failures:
        for failure in failures:
            print(f'FAILED: {failure}')
        return 1
    print(token)
    return 0


if __name__ == '__main__':
    sys.exit(validate())
