#!/usr/bin/env python3
"""Shared, position-based GATE ROOT inspection and canonical identity helpers."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = None


def stage_arguments(description, extra=None):
    global MANIFEST_PATH
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--manifest', type=Path)
    if extra:
        extra(parser)
    args = parser.parse_args()
    MANIFEST_PATH = args.manifest
    return args


def load_config():
    return json.loads((PROJECT_ROOT / 'config' / 'magiccube_config.json').read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def write_table(frame, path):
    """CSV is authoritative; an absent parquet engine never invalidates CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path.with_suffix('.csv'), index=False)
    try:
        frame.to_parquet(path.with_suffix('.parquet'), index=False)
        return True
    except ImportError:
        print('Parquet engine unavailable; CSV written.', file=sys.stderr)
        return False


def find_branch(frame, names):
    normalized = {''.join(c.lower() for c in str(k) if c.isalnum()): k for k in frame.columns}
    return next((normalized.get(''.join(c.lower() for c in name if c.isalnum()))
                 for name in names if ''.join(c.lower() for c in name if c.isalnum()) in normalized), None)


def read_tree(path, kind=None, tree_name=None):
    try:
        import uproot
    except ImportError as error:
        raise RuntimeError('ROOT inspection requires uproot in the runtime Python environment') from error
    with uproot.open(path) as root:
        candidates = [(str(key).split(';')[0], value) for key, value in root.items(recursive=True)
                      if hasattr(value, 'arrays') and hasattr(value, 'num_entries')]
        if tree_name:
            candidates = [(name, tree) for name, tree in candidates if name == tree_name]
        elif kind:
            candidates = [(name, tree) for name, tree in candidates
                          if kind.lower() in name.lower() or name.lower() == 'tree']
        if len(candidates) != 1:
            raise ValueError(f'{path}: expected one {kind or "data"} tree, found {[x[0] for x in candidates]}')
        name, tree = candidates[0]
        arrays = tree.arrays(library='np')
        if isinstance(arrays, np.ndarray) and arrays.dtype.names:
            arrays = {key: arrays[key] for key in arrays.dtype.names}
        frame = pd.DataFrame({key: value for key, value in arrays.items() if np.asarray(value).ndim == 1})
        if len(frame) != tree.num_entries:
            raise ValueError('Unable to preserve every ROOT entry')
        return {'file': str(path), 'tree_name': name, 'entry_count': int(tree.num_entries),
                'branch_names': list(tree.keys()), 'branch_dtypes': {k: str(v) for k, v in frame.dtypes.items()},
                'frame': frame}


def tree_names(path):
    import uproot
    with uproot.open(path) as root:
        return [str(key).split(';')[0] for key, value in root.items(recursive=True)
                if hasattr(value, 'arrays') and hasattr(value, 'num_entries')]


def detector_map():
    frame = pd.read_csv(PROJECT_ROOT / 'config' / 'detector_map.csv')
    for axis in 'xyz':
        if f'{axis}_mm' not in frame:
            for alias in (f'center_{axis}_mm', f'centre_{axis}_mm', f'global_{axis}_mm'):
                if alias in frame:
                    frame[f'{axis}_mm'] = frame[alias]
                    break
    required = ['detector_id', 'x_mm', 'y_mm', 'z_mm']
    if not set(required).issubset(frame):
        raise ValueError(f'detector_map.csv requires {required}')
    frame = frame.sort_values('detector_id').reset_index(drop=True)
    if len(frame) != 2048 or frame.detector_id.tolist() != list(range(2048)):
        raise ValueError('Canonical detector map must contain IDs 0..2047 exactly once')
    return frame


def source_manifest():
    path = MANIFEST_PATH or PROJECT_ROOT / 'runtime' / 'manifests' / 'simulation_manifest_validation.csv'
    if not path.exists():
        path = PROJECT_ROOT / 'config' / 'source_manifest.csv'
    frame = pd.read_csv(path)
    aliases = {'acquisition_s': ['duration_s', 'acq_s'], 'activity_bq': ['activity_Bq'],
               'replicate_id': ['replicate', 'replicate_index'], 'task_id': ['task_index'],
               **{f'source_{a}_mm': [f'{a}_mm'] for a in 'xyz'}}
    for name, alternatives in aliases.items():
        if name not in frame:
            for alias in alternatives:
                if alias in frame:
                    frame[name] = frame[alias]
                    break
    required = ['task_id', 'source_id', 'replicate_id', 'source_x_mm', 'source_y_mm', 'source_z_mm',
                'activity_bq', 'acquisition_s']
    if not set(required).issubset(frame):
        raise ValueError(f'Manifest requires {required}')
    if frame.task_id.duplicated().any() or frame[['source_id', 'replicate_id']].duplicated().any():
        raise ValueError('Task IDs and source/replicate pairs must be unique')
    if not np.isfinite(frame[required].to_numpy(dtype=float)).all():
        raise ValueError('Manifest contains non-finite values')
    for column in ('task_id', 'source_id', 'replicate_id'):
        values = frame[column].to_numpy(dtype=float)
        if (values < 0).any() or (values != np.floor(values)).any():
            raise ValueError(f'{column} must contain nonnegative integers')
        frame[column] = values.astype('int64')
    if (frame[['activity_bq', 'acquisition_s']] <= 0).any().any():
        raise ValueError('Activity and acquisition duration must be positive')
    for _, group in frame.groupby('source_id'):
        if (group[['source_x_mm', 'source_y_mm', 'source_z_mm', 'activity_bq']].nunique() != 1).any():
            raise ValueError('Replicates disagree about source position or activity')
    return frame.sort_values(['source_id', 'replicate_id']).reset_index(drop=True)


def map_positions(frame, kind='singles'):
    """Assign detector identity by unique cube containment, never volumeID indices."""
    mapping = detector_map()
    names = [('globalPos' + a.upper(), 'pos' + a.upper()) if kind == 'singles'
             else ('pos' + a.upper(), 'globalPos' + a.upper()) for a in 'xyz']
    columns = [find_branch(frame, options) for options in names]
    if any(column is None for column in columns):
        raise ValueError(f'{kind} requires global position XYZ branches for canonical mapping')
    positions = frame[columns].to_numpy(dtype=float)
    if not np.isfinite(positions).all():
        raise ValueError('Non-finite detector positions')
    centers = mapping[['x_mm', 'y_mm', 'z_mm']].to_numpy(dtype=float)
    half_sizes = np.column_stack([mapping[f'size_{a}_mm'].to_numpy(dtype=float) / 2
                                  if f'size_{a}_mm' in mapping else np.ones(len(mapping)) for a in 'xyz'])
    result = np.empty(len(frame), dtype=np.int64)
    for start in range(0, len(frame), 1000):
        inside = np.all(np.abs(positions[start:start + 1000, None, :] - centers[None, :, :])
                        <= half_sizes[None, :, :] + 1e-6, axis=2)
        matches = inside.sum(axis=1)
        if np.any(matches != 1):
            raise ValueError(f'{kind}: {int(np.count_nonzero(matches != 1))} positions unmapped or ambiguous in chunk {start}')
        result[start:start + len(inside)] = mapping.detector_id.to_numpy()[inside.argmax(axis=1)]
    return result


def validate_source_positions(frame, task):
    for axis in 'xyz':
        column = find_branch(frame, ['sourcePos' + axis.upper()])
        if column is not None and not np.allclose(frame[column].to_numpy(dtype=float), task[f'source_{axis}_mm'], atol=1e-5, rtol=0):
            raise ValueError(f'Source positions disagree with task {task.task_id}')


def main():
    args = stage_arguments(__doc__, lambda parser: parser.add_argument('paths', nargs='*', type=Path))
    paths = args.paths or sorted((PROJECT_ROOT / 'runtime' / 'sim').rglob('*.root'))
    if not paths:
        raise ValueError('No runtime ROOT files exist')
    reports = []
    for path in paths:
        for name in tree_names(path):
            kind = 'hits' if 'hits' in (name + path.name).lower() else 'singles'
            if not any(word in (name + path.name).lower() for word in ('hits', 'singles')):
                continue
            info = read_tree(path, tree_name=name)
            frame = info.pop('frame')
            ids = map_positions(frame, kind)
            reports.append({**info, 'canonical_detector_ids': np.unique(ids).tolist(),
                            'runID_present': find_branch(frame, ['runID']) is not None,
                            'eventID_present': find_branch(frame, ['eventID']) is not None})
    if not reports:
        raise ValueError('No Hits or Singles trees recognized')
    write_json(PROJECT_ROOT / 'results' / 'validation' / 'root_summary.json',
               {'files': reports, 'event_join_policy': 'source_id + replicate_id + runID + eventID; never eventID alone'})
    print(f'Inspected {len(reports)} ROOT files')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'ROOT inspection failed: {error}', file=sys.stderr)
        sys.exit(1)
