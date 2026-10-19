"""Small shared contracts for compact full-mode data; validation mode is unchanged."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from generate_source_positions import grid_axis
from inspect_root import PROJECT_ROOT as ROOT, detector_map, write_json
from merge_runtime_outputs import configured_gagg_families

MANIFEST = ROOT / 'runtime/manifests/simulation_manifest_full.csv'
SOURCES = ROOT / 'config/full_source_positions.csv'
SIM = ROOT / 'runtime/sim/full'
REDUCED = ROOT / 'runtime/reduced/full'
MATRIX = ROOT / 'results/system_matrix/full'
PPDF = ROOT / 'results/ppdf/full'
PLOTS = ROOT / 'results/plots/full'
PROVENANCE = ROOT / 'runtime/provenance/full'


def config(name):
    return json.loads((ROOT / 'config' / name).read_text())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def full_inputs(manifest=MANIFEST):
    """Verify actual coordinates and task rows against the configured grid, not a fixed count."""
    grid = config('source_grid_config.json')
    prod = config('production_config.json')
    require(grid['endpoint_status'] in ('EVIDENCE_CONFIRMED', 'PROJECT_CONVENTION_PENDING_EXTERNAL_CONFIRMATION'), 'Endpoint status missing')
    require(grid['source_model'].lower() == 'point' and grid['angular_distribution'] == 'isotropic', 'Point/isotropic contract changed')
    axes = {a: grid_axis(grid[f'fov_{a}_mm'], grid[f'spacing_{a}_mm'], grid['center_mm'][a], grid['endpoint_mode']) for a in 'xy'}
    for a in 'xy':
        require(grid[f'fov_{a}_mm'] == grid['fov_mm'][a] and grid[f'spacing_{a}_mm'] == grid['spacing_mm'][a], 'Grid aliases disagree')
    require(grid['activity_bq'] == grid['activity_Bq'] and grid['acquisition_s'] == grid['acquisition_time_s'], 'Exposure aliases disagree')
    require(grid['replicates_per_source'] == grid['replicates'], 'Replicate aliases disagree')
    source = pd.read_csv(SOURCES)
    expected = np.array([(x, y, grid['z_mm']) for y in axes['y'] for x in axes['x']], dtype=float)
    require(np.array_equal(source.source_id, np.arange(len(expected))), 'Source IDs/order inconsistent')
    require(not source[['x_mm', 'y_mm', 'z_mm']].duplicated().any(), 'Duplicate source coordinates')
    require(np.array_equal(source[['x_mm', 'y_mm', 'z_mm']].to_numpy(), expected), 'Source coordinates/order inconsistent with endpoint config')
    for column in ('energy_keV', 'activity_bq', 'acquisition_s'):
        require(np.all(source[column] == grid[column]), f'Source {column} inconsistent')
    require((grid['z_mm'], grid['energy_keV'], grid['activity_bq'], grid['acquisition_s']) == (-66.0, 140.0, 3700000.0, 1.0), 'Frozen production source contract changed')
    tasks = pd.read_csv(manifest)
    replicas = grid['replicates_per_source']
    require(isinstance(replicas, int) and replicas > 0, 'Invalid replicate count')
    expected_pairs = [(int(s), r) for s in source.source_id for r in range(replicas)]
    require(len(tasks) == len(expected_pairs), 'Manifest count does not equal sources times replicates')
    require(np.array_equal(tasks.task_id, np.arange(len(tasks))), 'Task IDs not contiguous/in deterministic order')
    require(list(zip(tasks.source_id, tasks.replicate_id)) == expected_pairs, 'Missing/duplicate/reordered source-replicate task')
    require(np.array_equal(tasks.seed, prod['seed_base'] + np.arange(len(tasks))), 'Seeds differ from deterministic policy')
    require(tasks.seed.is_unique and (tasks.seed > 0).all() and (tasks.seed <= 2147483647).all(), 'Invalid or duplicate seeds')
    for column in ('x_mm', 'y_mm', 'z_mm', 'activity_bq', 'acquisition_s'):
        require(np.array_equal(tasks[column], source.set_index('source_id').loc[tasks.source_id, column].to_numpy()), f'Manifest {column} inconsistent')
    require(np.all(tasks.expected_emitted_photons == tasks.activity_bq * tasks.acquisition_s), 'Expected emission metadata inconsistent')
    for a in 'xyz':
        tasks[f'source_{a}_mm'] = tasks[f'{a}_mm']
    return source, tasks, detector_map()


def prefix(task):
    return f'source_{int(task.source_id):04d}_rep_{int(task.replicate_id):03d}'


def task_paths(task):
    return (SIM / f'task_{int(task.task_id):06d}.exit_code.txt',
            SIM / f'task_{int(task.task_id):06d}.metadata.json',
            REDUCED / f'{prefix(task)}.npz', REDUCED / f'{prefix(task)}.json')


def family_files(task, kind):
    families = configured_gagg_families()
    label = 'hits' if kind == 'hits' else 'Singles'
    paths = [(family, SIM / f'{prefix(task)}.{label}_{family}.root') for family in families]
    for _, path in paths:
        require(path.is_file(), f'Task {int(task.task_id)} missing {path.name}')
    return paths


def provenance_files():
    return [ROOT / rel for rel in ('config/magiccube_config.json', 'config/source_grid_config.json',
            'config/production_config.json', 'config/detector_map.csv', 'config/detector_map.parquet',
            'config/full_source_positions.csv', 'config/full_source_positions.parquet',
            'runtime/manifests/simulation_manifest_full.csv')] + sorted((ROOT / 'GATE-Macro').glob('*.mac')) + [ROOT / 'GATE-Macro/GateMaterials.db'] + [
                ROOT / 'scripts' / name for name in ('production_common.py', 'inspect_root.py', 'render_gate_macro.py',
                'reduce_source_response.py', 'aggregate_system_matrix.py', 'generate_full_ppdf.py', 'plot_full_response.py',
                'record_full_task.py', 'run_full_shard.py', 'validate_full_runtime.py')]


def current_identity():
    files = {str(path.relative_to(ROOT)): sha256(path) for path in provenance_files()}
    fingerprint = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {'fingerprint': fingerprint, 'files': files}


def verify_provenance():
    record = json.loads((PROVENANCE / 'run_metadata.json').read_text())
    require(record['identity'] == current_identity(), 'Production inputs changed: do not combine incompatible runs')
    for rel, digest in record['identity']['files'].items():
        require(sha256(PROVENANCE / 'inputs' / rel) == digest, f'Provenance copy changed: {rel}')
    return record['identity']['fingerprint']


def load_reduced(task, fingerprint, detector_ids):
    _, _, path, meta_path = task_paths(task)
    meta = json.loads(meta_path.read_text())
    require(meta['fingerprint'] == fingerprint, f'{path.name}: provenance mismatch')
    require(meta['npz_sha256'] == sha256(path), f'{path.name}: checksum mismatch')
    with np.load(path, allow_pickle=False) as data:
        require(np.array_equal(data['detector_id'], detector_ids), f'{path.name}: detector ordering mismatch')
        counts = data['raw_singles_count'].copy()
        require(counts.shape == (len(detector_ids),) and np.issubdtype(counts.dtype, np.integer) and (counts >= 0).all(), f'{path.name}: invalid response vector')
        for name in ('task_id', 'source_id', 'replicate_id', 'seed', 'activity_bq', 'acquisition_s'):
            require(data[name].item() == task[name] and meta[name] == task[name], f'{path.name}: {name} mismatch')
        for a in 'xyz':
            require(data[f'source_{a}_mm'].item() == task[f'{a}_mm'] and meta[f'source_{a}_mm'] == task[f'{a}_mm'], f'{path.name}: source coordinate mismatch')
    require(int(counts.sum()) == meta['raw_total_singles'] == sum(meta['singles_by_family'].values()), f'{path.name}: count conservation failed')
    require(meta['detector_rows'] == len(detector_ids), f'{path.name}: row count mismatch')
    return counts, meta


def write_long_parquet(path, raw, sources, value=None, value_name=None, duration=None):
    """Stream one source column per row group; no global event table or multi-million-row frame."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    try:
        for j, source in sources.iterrows():
            fields = {'detector_id': np.arange(raw.shape[0], dtype=np.int64), 'source_id': np.repeat(int(source.source_id), raw.shape[0]),
                      **{f'source_{a}_mm': np.repeat(float(source[f'{a}_mm']), raw.shape[0]) for a in 'xyz'},
                      'raw_singles_count': raw[:, j]}
            if value_name == 'cps_per_bq':
                fields.update(acquisition_s=np.repeat(float(duration[j]), raw.shape[0]),
                              activity_bq=np.repeat(float(source.activity_bq), raw.shape[0]),
                              cps_per_bq=value[:, j], cps_per_mbq=value[:, j] * 1e6)
            elif value_name:
                fields[value_name] = value[:, j]
            table = pa.Table.from_pydict(fields)
            if writer is None:
                writer = pq.ParquetWriter(path, table.schema, compression='snappy')
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
