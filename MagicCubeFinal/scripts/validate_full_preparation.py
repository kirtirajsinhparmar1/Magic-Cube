#!/usr/bin/env python3
"""Authoritative full-FOV static checks: never runs GATE, reads runtime events, or submits jobs."""
import json
import re
import subprocess
import sys

import numpy as np
import pandas as pd

from production_common import ROOT, config, full_inputs, sha256, verify_provenance


def main():
    failures, checks = [], {}

    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            failures.append(name)

    try:
        for path in sorted((ROOT / 'config').glob('*.json')):
            json.loads(path.read_text())
        check('configuration_json', True)
        sources, tasks, mapping = full_inputs()
        check('derived_grid_source_ids_coordinates_and_spacing', True)
        check('derived_manifest_count_order_exposure_and_unique_seeds', True)
        check('source_parquet_matches_csv', pd.read_parquet(ROOT / 'config/full_source_positions.parquet').equals(sources))
        check('canonical_detector_dimension', len(mapping) == len(mapping.detector_id.unique()) and
              np.array_equal(mapping.detector_id, np.arange(len(mapping))))
        grid, prod = config('source_grid_config.json'), config('production_config.json')
        check('published_target_grid_parameters', (grid['fov_x_mm'], grid['fov_y_mm'], grid['spacing_x_mm'],
              grid['spacing_y_mm'], grid['z_mm'], grid['energy_keV']) == (100, 100, 2, 2, -66, 140))
        check('endpoint_mode_explicit', grid['endpoint_mode'] in ('centered_inclusive', 'inclusive', 'voxel_centers'))
        check('endpoint_status_explicit', grid['endpoint_status'] in ('EVIDENCE_CONFIRMED', 'PROJECT_CONVENTION_PENDING_EXTERNAL_CONFIRMATION'))
        check('concurrency_configured', isinstance(prod['full_array_max_concurrent'], int) and prod['full_array_max_concurrent'] > 0)
        shards = prod['full_worker_shards']
        check('worker_shards_configured', isinstance(shards, int) and 0 < shards <= len(tasks))
        check('worker_walltime_configured', isinstance(prod['full_worker_walltime'], str) and
              bool(re.fullmatch(r'(?:\d+-)?\d{1,2}:\d{2}:\d{2}', prod['full_worker_walltime'])))
        assigned = [int(task_id) for shard in range(shards) for task_id in range(shard, len(tasks), shards)]
        expected_tasks = tasks.task_id.astype(int).tolist()
        check('shard_assignment_covers_manifest_exactly_once', sorted(assigned) == expected_tasks and
              len(assigned) == len(set(assigned)) and all(task_id % shards == assigned_shard
              for assigned_shard in range(shards) for task_id in range(assigned_shard, len(tasks), shards)))
        ids = prod['plot_detector_ids']
        expected_ids = mapping.detector_id.tolist() if ids == 'all' else ids
        plot_manifest = pd.read_csv(ROOT / 'runtime/manifests/plot_manifest_full.csv')
        check('plot_manifest_subset_or_all', np.array_equal(plot_manifest.task_id, np.arange(len(expected_ids))) and
              np.array_equal(plot_manifest.detector_id, expected_ids) and len(set(expected_ids)) == len(expected_ids) and
              all(i in mapping.detector_id.values for i in expected_ids))
        verify_provenance()
        check('provenance_input_snapshots_and_checksums', True)
    except Exception as error:
        failures.append(f'Configuration/artifact checks: {error}')

    try:
        baseline = config('full_frozen_baseline.json')['files']
        for rel, digest in baseline.items():
            check(f'frozen_{rel}', sha256(ROOT / rel) == digest)
    except Exception as error:
        failures.append(f'Frozen-file regression guard: {error}')

    for path in sorted(ROOT.rglob('*.py')):
        try:
            compile(path.read_text(), str(path), 'exec')
        except Exception as error:
            failures.append(f'Python syntax {path.relative_to(ROOT)}: {error}')
    check('python_compilation', not any(f.startswith('Python syntax ') for f in failures))
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and path.suffix in ('.sh', '.slurm'):
            result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
            if result.returncode:
                failures.append(f'Bash syntax {path.relative_to(ROOT)}: {result.stderr.strip()}')
    check('shell_syntax', not any(f.startswith('Bash syntax ') for f in failures))

    try:
        text = lambda name: (ROOT / name).read_text()
        orchestrator = text('slurm/par_full.sh')
        check('manifest_derived_sharded_simulation_array', 'simulation_manifest_full.csv' in orchestrator and
              'full_worker_shards' in orchestrator and '0-$((SHARDS-1))' in orchestrator and
              '0-$((N-1))' not in orchestrator and 'magiccube_full_shard.slurm' in orchestrator)
        check('complete_dependency_graph', all(s in orchestrator for s in (
            'magiccube_full_shard.slurm', 'magiccube_aggregate.slurm', 'magiccube_full_ppdf.slurm',
            'magiccube_full_plot.slurm', 'magiccube_heatmap.slurm', 'magiccube_validate.slurm',
            'afterok:$sim', 'afterok:$matrix', 'afterok:$ppdf:$matrix', 'afterok:$ppdf', 'afterok:$plots:$heatmaps')) and
              'magiccube_reduce.slurm' not in orchestrator)
        check('full_mode_no_global_event_merge', 'magiccube_merge.slurm' not in orchestrator and
              'merge_runtime_outputs.py' not in orchestrator and 'MAGICCUBE_MODE=full' in orchestrator)
        check('robust_quoted_root_propagation', 'MAGICCUBE_ROOT="$ROOT"' in orchestrator and
              'ALL,MAGICCUBE_ROOT,MAGICCUBE_MANIFEST,MAGICCUBE_MODE' in orchestrator)
        worker_paths = sorted((ROOT / 'slurm').glob('*.slurm'))
        check('workers_no_nested_submission', all('sbatch' not in p.read_text() for p in worker_paths))
        check('worker_root_from_environment', all('ROOT="${MAGICCUBE_ROOT:?' in p.read_text() for p in worker_paths))
        simulation = text('slurm/magiccube_sim.slurm')
        shard_worker = text('slurm/magiccube_full_shard.slurm')
        shard_runner = text('scripts/run_full_shard.py')
        validated_gate_environment = "\n".join((
            'module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2',
            'export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"',
            'module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2',
        ))
        check('simulation_resources_preserved', '#SBATCH --cpus-per-task=1' in shard_worker and '#SBATCH --mem=4G' in shard_worker)
        check('full_shard_reuses_validated_gate_environment', validated_gate_environment in simulation and
              validated_gate_environment in shard_worker)
        preflight = shard_worker.find('command -v Gate')
        runner_exec = shard_worker.find('exec env -u PYTHONPATH "$PY" "$ROOT/scripts/run_full_shard.py"')
        check('full_shard_gate_preflight_before_source_loop', shard_worker.count('command -v Gate') == 1 and
              shard_worker.count('Gate --version') == 1 and
              'Gate executable unavailable' in shard_worker and 0 <= preflight < runner_exec and
              'for _, task in assigned.iterrows()' in shard_runner)
        check('full_shard_worker_contract', all(s in shard_worker for s in ('SLURM_ARRAY_TASK_ID', 'full_worker_shards', 'run_full_shard.py')) and
              all(s in shard_runner for s in ('task_id) % args.shards', 'render_gate_macro.py', 'Gate", "main.mac',
              'reduce_source_response.py', 'complete_task', 'return 1 if results["failed"]')))
        check('full_runtime_namespace_and_exit_metadata', all(s in shard_runner for s in (
              'runtime" / "generated_macros" / "full',
              'runtime" / "logs" / "full',
              'record_full_task.py')))
        reducer = text('scripts/reduce_source_response.py')
        check('all_family_chunked_position_mapping', all(s in reducer for s in ('family_files(task', 'gagg_family', 'map_positions',
              'validate_source_positions', '.iterate(', 'np.bincount', 'len(mapping)')))
        check('complete_zero_inclusive_detector_vectors', 'np.zeros(len(mapping)' in reducer and 'raw_singles_count' in reducer)
        check('no_event_csv_in_reducer', 'to_csv' not in reducer and 'to_parquet' not in reducer)
        aggregate = text('scripts/aggregate_system_matrix.py')
        check('raw_and_absolute_dense_matrices', all(s in aggregate for s in ('len(mapping), len(sources)', 'load_reduced',
              'raw[:, j] += counts', 'duration[j] +=', 'duration * sources.activity_bq', 'system_matrix_raw.npy', 'system_matrix.npy', 'write_long_parquet')))
        ppdf = text('scripts/generate_full_ppdf.py')
        check('matrix_based_zero_safe_ppdf', all(s in ppdf for s in ('system_matrix_raw.npy', 'sum(axis=1)', 'np.divide', 'out=np.zeros',
              'where=totals[:, None] > 0', 'ppdf.npy', 'write_long_parquet')) and 'singles_canonical' not in ppdf)
        check('streamed_long_parquet', 'pq.ParquetWriter' in text('scripts/production_common.py') and 'for j, source in sources.iterrows()' in text('scripts/production_common.py'))
        check('sensitivity_summary_available', all(s in aggregate for s in ('sensitivity_summary.json', "'central'", "'mean'", "'min'", "'max'", 'scientific_agreement_claimed')))
        resume = text('scripts/find_incomplete_tasks.py')
        recorder = text('scripts/record_full_task.py')
        check('failed_exit_markers_remain_incomplete', 'marker.read_text().strip() != "0"' in shard_runner and
              'info.get("gate_exit_code") != 0' in shard_runner and "state != '0'" in resume and
              'simulation_incomplete.append(tid)' in resume and 'marker.write_text' in recorder)
        check('resume_diagnostics_no_resubmission', (ROOT / 'scripts/find_incomplete_tasks.py').is_file() and
              'sbatch' not in text('scripts/find_incomplete_tasks.py') and 'incomplete_shard_ids' in text('scripts/find_incomplete_tasks.py'))
        check('full_runtime_validator_route_and_token', 'from validate_full_runtime import validate' in text('scripts/validate_runtime.py') and
              'MAGICCUBE_FULL_MATRIX_PASS' in text('scripts/validate_full_runtime.py'))
        check('full_grid_plotting_and_all_detector_support', all(s in text('scripts/plot_full_response.py') for s in
              ('PPDF_Detector_', 'plot-index', 'pivot(', 'sensitivity_map.png', 'detector_geometry.png')) and
              "selected == 'all'" in text('scripts/prepare_full_run.py'))
        check('no_raw_output_cleanup', all(s not in reducer + aggregate + orchestrator for s in ('rmtree(', '.unlink(', 'rm -', 'remove(')))
        check('required_full_documentation', all((ROOT / name).is_file() for name in ('FULL_FOV_GRID_REPORT.md', 'FULL_PRODUCTION_RUNBOOK.md', 'FULL_FOV_BUILD_RESULTS.md')))
    except Exception as error:
        failures.append(f'Production architecture checks: {error}')

    for failure in failures:
        print(f'FAILED: {failure}')
    report = {'checks': checks, 'failures': failures, 'passed': not failures, 'runtime_executed': False}
    target = ROOT / 'results/validation/full/preparation_validation.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n')
    print('MAGICCUBE FULL-FOV STATIC PREPARATION: ' + ('FAIL' if failures else 'PASS'))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
