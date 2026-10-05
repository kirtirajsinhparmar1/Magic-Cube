#!/usr/bin/env python3
"""Merge family-qualified Singles and Hits with canonical detector context."""
import sys
from pathlib import Path

import pandas as pd

from inspect_root import (PROJECT_ROOT, load_config, map_positions, read_tree, source_manifest,
                          validate_source_positions, write_json, write_table, stage_arguments)


EXPECTED_GAGG_FAMILIES = (
    'mc_gagg_ee',
    'mc_gagg_eo',
    'mc_gagg_oe',
    'mc_gagg_oo',
)


def configured_gagg_families():
    """Return the explicitly configured GAGG family names in deterministic order."""
    configured = tuple(load_config().get('output', {}).get('singles_families', ()))
    if configured != EXPECTED_GAGG_FAMILIES:
        raise ValueError(
            'Configured GAGG family set/order must be '
            f'{EXPECTED_GAGG_FAMILIES}, got {configured}'
        )
    return configured


def discover_family_files(directory, prefix, kind, families, task_id):
    """Resolve exactly one configured family file for a task and output kind."""
    filename_kind = {'hits': 'hits', 'singles': 'Singles'}[kind]
    found = {}
    for family in families:
        pattern = f'{prefix}.{filename_kind}_{family}.root'
        # Validation shards are direct children; production has its own namespace.
        matches = sorted(directory.glob(pattern))
        if len(matches) != 1:
            rendered = ', '.join(str(path) for path in matches) or 'none'
            raise ValueError(
                f'Task {task_id}: expected exactly one {pattern} under {directory}, '
                f'found {len(matches)} ({rendered})'
            )
        found[family] = matches[0]
    return found


def task_directory(task):
    for column in ('output_dir', 'runtime_dir', 'raw_dir', 'task_output_dir'):
        if column in task and pd.notna(task[column]):
            path = Path(str(task[column]))
            return path if path.is_absolute() else PROJECT_ROOT / path
    raw = PROJECT_ROOT / 'runtime' / 'raw'
    candidates = [raw / f'task_{int(task.task_id):06d}', raw / f'task_{int(task.task_id):04d}',
                  raw / f'task_{int(task.task_id)}', raw / str(int(task.task_id))]
    existing = [path for path in candidates if path.is_dir()]
    if len(existing) != 1:
        raise ValueError(f'Task {task.task_id}: expected one output directory, found {existing}')
    return existing[0]


def main():
    stage_arguments(__doc__)
    manifest = source_manifest()
    families = configured_gagg_families()
    parts = {'singles': [], 'hits': []}
    files = []
    family_counts = {'singles': {}, 'hits': {}}
    for _, task in manifest.iterrows():
        sim = PROJECT_ROOT / 'runtime' / 'sim'
        prefix = f'source_{int(task.source_id):04d}_rep_{int(task.replicate_id):03d}'
        directory = sim if sim.is_dir() else task_directory(task)
        family_paths = {
            kind: discover_family_files(directory, prefix, kind, families, task.task_id)
            for kind in ('hits', 'singles')
        }
        singles_found = False
        for kind in ('hits', 'singles'):
            for family, path in family_paths[kind].items():
                # Each validated GATE family file contains the common tree;1 tree.
                info = read_tree(path, tree_name='tree')
                frame = info.pop('frame')
                validate_source_positions(frame, task)
                frame['detector_id'] = map_positions(frame, kind)
                for column in ('task_id', 'source_id', 'replicate_id'):
                    # GATE sourceID is local to each acquisition; manifest source_id is canonical.
                    frame[column] = int(task[column])
                for column in ('source_x_mm', 'source_y_mm', 'source_z_mm',
                               'activity_bq', 'acquisition_s'):
                    frame[column] = float(task[column])
                frame['gagg_family'] = family
                frame['origin_file'] = str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path)
                frame['origin_tree'] = 'tree'
                parts[kind].append(frame)
                family_counts[kind][family] = family_counts[kind].get(family, 0) + len(frame)
                files.append({**info, 'kind': kind, 'gagg_family': family,
                              'task_id': int(task.task_id)})
                if kind == 'singles':
                    singles_found = True
        if not singles_found:
            raise ValueError(f'Task {task.task_id} has no Singles tree (empty Singles trees are permitted)')
    out = PROJECT_ROOT / 'runtime' / 'merged'
    counts = {}
    for kind, frames in parts.items():
        if frames:
            merged = pd.concat(frames, ignore_index=True, sort=False)
            write_table(merged, out / (kind + '_canonical'))
            counts[kind] = len(merged)
    write_json(out / 'merge_summary.json', {'files': files, 'counts': counts,
               'family_counts': family_counts,
               'required_gagg_families': list(families),
               'task_ids': manifest.task_id.astype(int).tolist(),
               'canonical_mapping': 'unique containment in detector_map.csv cubes using global XYZ',
               'event_join_policy': 'source_id + replicate_id + runID + eventID; rows are never deduplicated'})
    print(f'Merged counts: {counts}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'Runtime merge failed: {error}', file=sys.stderr)
        sys.exit(1)
