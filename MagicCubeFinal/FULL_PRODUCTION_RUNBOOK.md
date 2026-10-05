# Full production runbook

Preparation only: no GATE or scheduler job was executed during this build. The successful 2048 x 1 validation remains the detector-side reference. The next simulation is the entire configured source FOV, not a pilot.

## Static preparation

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal"
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/validate_preparation.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/validate_full_preparation.py
```

The full token is `MAGICCUBE FULL-FOV STATIC PREPARATION: PASS`. Static checks do not establish scientific agreement or runtime success.

## Launch the entire FOV

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal/slurm"
bash par_full.sh
```

The orchestrator deterministically regenerates/verifies the full source table and manifest, prepares provenance snapshots and plot selection, then submits: simulation array -> reduction array -> matrix aggregation -> PPDF -> global plots + heatmap array -> full validation. All submissions use parsable job IDs and explicit `afterok` dependencies. Workers never submit jobs. Both source arrays derive their bounds from the same manifest. `MAGICCUBE_ROOT` is exported by the direct shell orchestrator and consumed by every worker; paths containing spaces remain quoted.

Full namespaces are `runtime/sim/full`, `runtime/generated_macros/full`, `runtime/logs/full`, `runtime/reduced/full`, `runtime/provenance/full`, and corresponding `results/*/full` directories. The successful validation outputs and `par_validation.sh` remain separate.

GATE retains its proven 1 CPU / 4 GB per task. `config/production_config.json` sets `full_array_max_concurrent: 16`; this is a concurrency ceiling, not guaranteed allocation. Sixteen 4-GB tasks request 64 GB collectively, so a 40-GB allocation may schedule fewer concurrently. Change only this configured ceiling before launch when appropriate; per-task GATE resources are unchanged. Configuration adjustments before any production data exist can refresh preparation snapshots. Once ROOT/exit-marker/reduced data exist, incompatible input changes are rejected to prevent mixed runs.

## Data products

Raw ROOT -> per-task canonical 2048-vector -> aggregate matrix -> PPDF/plots/validation. All four explicit GAGG families are required. Canonical detector identity comes from the frozen position-derived map; family is additional consistency evidence, not an ID. ROOT reads are chunked and Hits are inspected diagnostically by header. Zero-count detectors remain present. There is no global full-production event CSV and no automatic ROOT cleanup.

Each reduction writes `runtime/reduced/full/source_<id>_rep_<rep>.npz` and `.json`. NPZ stores the full detector-ID/count vectors and task/source/replicate/position/exposure/seed metadata; JSON records family totals, source-file inventory, checksums, provenance, and count conservation.

`results/system_matrix/full/system_matrix_raw.npy` retains integer counts. `system_matrix.npy` is absolute response in counts / second / Bq. Replicate counts and acquisition durations are summed per source; activity is common within the source condition. `system_matrix.parquet` streams one source column per row group, including raw counts, exposure, coordinates, cps/Bq, and cps/MBq. No large CSV is required.

`results/ppdf/full/ppdf.npy` and `ppdf.parquet` use the raw matrix, normalized across source columns per detector. Zero-response rows remain zero. Sensitivity CSV/Parquet and JSON summary report per-source sensitivity, FOV arithmetic mean, min/max, central sensitivity, the 5916 cps/MBq comparison target, and relative difference without tuning or claiming agreement.

## Plot selection

`production_config.plot_detector_ids` defaults to [0,512,1024,1536]. Set it to `"all"` before launch to submit every detector heatmap, without changing simulation coverage. The plot manifest determines array bounds. Individual additional heatmaps may be generated from the completed matrix without resimulation or configuration changes:

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal"
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/plot_full_response.py --detector-id 17
```

Global plots cover detector/material centers, canonical IDs, source plane/grid, selected-detector PPDF support, absolute response, sensitivity map, and detector totals. Heatmaps are named `PPDF_Detector_<id>.png`.

## Failure diagnosis and continuation

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal"
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/find_incomplete_tasks.py
```

This read-only command reports complete/missing/failed task IDs plus `simulation_array` and `reduction_array` specifications. It does not submit or retry jobs. Simulation arrays contain only tasks with missing/failed simulation evidence; reduction arrays identify tasks whose existing ROOT outputs can be reused. Keep raw files. Resubmit only the printed task IDs using the existing workers, the same `MAGICCUBE_ROOT`, `MAGICCUBE_MANIFEST`, and `MAGICCUBE_MODE=full`, and the appropriate concurrency cap. A failed array leaves its original `afterok` dependents blocked; after repairing required tasks, deliberately restart the blocked downstream stages rather than rerunning successful simulations.

After every required compact vector exists, the existing downstream scripts can also be invoked manually (not performed during preparation):

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal"
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/aggregate_system_matrix.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/generate_full_ppdf.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/plot_full_response.py --global
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/plot_full_response.py --detector-id 0
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/plot_full_response.py --detector-id 512
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/plot_full_response.py --detector-id 1024
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/plot_full_response.py --detector-id 1536
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/validate_runtime.py --mode full
```

Those heatmap IDs reflect the default plot configuration; use the configured plot-manifest IDs if changed. Full runtime validation checks all task exit markers, four-family readable ROOT shards, compact vectors, count/exposure conservation, ordering, source coordinates, long/dense matrices, PPDF, required plots, and provenance. Its success token is `MAGICCUBE_FULL_MATRIX_PASS`, recorded in `results/validation/full/runtime_validation.json`. Do not interpret a static PASS as that runtime token.
