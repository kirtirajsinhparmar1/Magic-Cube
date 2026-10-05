#!/usr/bin/env python3
"""Validate count conservation, canonical coverage, exposure and PPDF normalization."""
import json
import sys

import numpy as np
import pandas as pd

import inspect_root
from generate_ppdf import response_table
from inspect_root import PROJECT_ROOT, stage_arguments, write_json


def main():
    args = stage_arguments(__doc__, lambda parser: parser.add_argument('--mode', choices=['validation', 'full'], default='validation'))
    if args.mode == 'full':
        from validate_full_runtime import validate
        return validate(args.manifest)
    if args.manifest is None:
        inspect_root.MANIFEST_PATH = PROJECT_ROOT / 'runtime' / 'manifests' / f'simulation_manifest_{args.mode}.csv'
    failures = []
    checks = {}
    def check(name, passed):
        checks[name] = bool(passed)
        if not passed:
            failures.append(name)
    try:
        expected, sources = response_table()
        ppdf = pd.read_csv(PROJECT_ROOT / 'results' / 'ppdf' / 'ppdf.csv')
        matrix = pd.read_csv(PROJECT_ROOT / 'results' / 'system_matrix' / 'system_matrix.csv')
        raw = np.load(PROJECT_ROOT / 'results' / 'system_matrix' / 'system_matrix_raw.npy', allow_pickle=False)
        normalized = np.load(PROJECT_ROOT / 'results' / 'system_matrix' / 'system_matrix.npy', allow_pickle=False)
        metadata = json.loads((PROJECT_ROOT / 'results' / 'system_matrix' / 'system_matrix_metadata.json').read_text())
        merge = json.loads((PROJECT_ROOT / 'runtime' / 'merged' / 'merge_summary.json').read_text())
        shape = (2048, len(sources))
        check('validation_has_one_source', args.mode != 'validation' or len(sources) == 1)
        check('complete_shape', raw.shape == shape and normalized.shape == shape)
        check('raw_integer_dtype', np.issubdtype(raw.dtype, np.integer))
        check('normalized_float_dtype', np.issubdtype(normalized.dtype, np.floating))
        check('metadata_order', metadata['source_ids'] == sources.source_id.astype(int).tolist() and metadata['detector_ids'] == list(range(2048)))
        check('all_manifest_tasks_merged', sorted(merge['task_ids']) == sorted(inspect_root.source_manifest().task_id.astype(int).tolist()))
        expected_keys = expected[['detector_id', 'source_id']].to_numpy()
        for label, frame in [('ppdf', ppdf), ('system_matrix', matrix)]:
            check(f'{label}_complete_order', len(frame) == len(expected) and np.array_equal(frame[['detector_id', 'source_id']].to_numpy(), expected_keys))
            if len(frame) == len(expected):
                check(f'{label}_raw_counts', np.array_equal(frame.raw_singles_count.to_numpy(), expected.raw_singles_count.to_numpy()))
                for axis in 'xyz':
                    check(f'{label}_source_{axis}', np.allclose(frame[f'source_{axis}_mm'], expected[f'source_{axis}_mm'], rtol=0, atol=1e-8))
        check('count_conservation', int(raw.sum()) == int(expected.raw_singles_count.sum()) == merge['counts']['singles'])
        check('diagnostic_hits_present', merge['counts'].get('hits', 0) > 0)
        check('positive_smoke_counts', args.mode != 'validation' or int(raw.sum()) > 0)
        check('nonnegative_finite_response', np.isfinite(normalized).all() and (normalized >= 0).all())
        expected_response = expected.raw_singles_count.to_numpy() / (expected.activity_bq.to_numpy() * expected.acquisition_s.to_numpy())
        check('raw_dense_matches', raw.shape == shape and np.array_equal(raw.reshape(-1), expected.raw_singles_count.to_numpy()))
        check('normalization', normalized.shape == shape and np.allclose(normalized.reshape(-1), expected_response, atol=1e-14, rtol=1e-10))
        if len(matrix) == len(expected):
            check('long_normalization', np.allclose(matrix.cps_per_bq, expected_response) and np.allclose(matrix.cps_per_mbq, expected_response * 1e6))
            check('exposure_fields', np.allclose(matrix.acquisition_s, expected.acquisition_s) and np.allclose(matrix.activity_bq, expected.activity_bq))
        if len(ppdf) == len(expected):
            check('ppdf_normalization', np.isfinite(ppdf.ppdf).all() and np.allclose(ppdf.ppdf, expected.ppdf, atol=1e-12, rtol=1e-10))
        for name in ('positions.png', 'system_matrix_heatmap.png'):
            path = PROJECT_ROOT / 'results' / 'plots' / name
            check(f'plot_{name}', path.is_file() and path.stat().st_size > 0)
        selected_plots = list((PROJECT_ROOT / 'results' / 'plots').glob('PPDF_Detector_*.png'))
        check('selected_detector_spatial_ppdf', any(path.stat().st_size > 0 for path in selected_plots))
    except Exception as error:
        failures.append(f'Runtime validation could not complete: {error}')
    token = 'MAGICCUBE_2048x1_END_TO_END_PASS' if args.mode == 'validation' else 'MAGICCUBE_FULL_END_TO_END_PASS'
    write_json(PROJECT_ROOT / 'results' / 'validation' / f'runtime_validation_{args.mode}.json',
               {'mode': args.mode, 'checks': checks, 'failures': failures, 'passed': not failures,
                'pass_token': token if not failures else None})
    if failures:
        for failure in failures:
            print(f'FAILED: {failure}')
        return 1
    print(token)
    return 0


if __name__ == '__main__':
    sys.exit(main())
