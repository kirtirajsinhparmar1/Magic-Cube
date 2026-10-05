# Full-FOV build results

Task: full-FOV production preparation. Status: **PASS**. Both static validators passed on the first validation pass; no correction pass was needed. No full-production runtime PASS is claimed.

Implemented: deterministic full-grid/source manifest generation, four-family chunked per-task canonical count reduction, compact-vector matrix aggregation, matrix-based PPDF, sensitivity summaries, full-grid/global and configurable detector heatmaps, provenance snapshots, resume diagnostics, production Slurm dependencies, and full static/runtime validation. The validated one-source path is retained.

Frozen detector geometry, materials, system, physics, digitizer, source/output templates, detector map (CSV/Parquet), and validation orchestrator matched all ten pre-edit SHA-256 hashes. No frozen file was changed. The existing reference-isolation checks passed and the repository tracked diff was empty; implementation additions/edits are confined to MagicCubeFinal.

The bounded evidence check did not determine exact source endpoints. The explicit engineering convention is `centered_inclusive`, with status `PROJECT_CONVENTION_PENDING_EXTERNAL_CONFIRMATION`: x/y -50..+50 mm at 2 mm spacing, 51 x 51 = 2601 positions; z=-66 mm. Source order is y outer/x inner. Point/isotropic gamma, 140 keV, 3.7e6 Bq and 1 s, one replicate/source.

Generated and checked: `config/full_source_positions.csv` and `.parquet`, each with 2601 sources, IDs 0..2600, no duplicated coordinates, 51 unique x and y positions, y outer/x inner ordering; `runtime/manifests/simulation_manifest_full.csv` with 2601 tasks, IDs 0..2600, replicate ID 0, and unique deterministic seeds 1,000,001..1,002,601. Production input snapshots and run metadata were generated under `runtime/provenance/full`; the plot manifest contains four configured detector tasks.

Data flow: `raw ROOT -> per-source 2048-vector -> aggregate matrix`. No global production event CSV; all raw ROOT shards retained. Simulation and reduction arrays -> aggregation -> PPDF -> global plots + heatmap array -> full validation. Resume diagnostics print incomplete IDs without resubmission.

Expected dense raw/absolute/PPDF shape is (2048,2601): 5,326,848 elements/reduced detector-source entries and 20,808 expected ROOT family shards. Raw counts: `results/system_matrix/full/system_matrix_raw.npy`; absolute cps/Bq: `system_matrix.npy`; PPDF: `results/ppdf/full/ppdf.npy`. Long Parquet keeps counts and source metadata. Replicate counts and exposure durations are summed, not duplicated into columns.

Resources: GATE remains 1 CPU and 4 GB/task. `config/production_config.json` controls `full_array_max_concurrent=16`. This is a ceiling; sixteen 4-GB tasks total 64 GB requested and may not all fit a 40-GB allocation simultaneously. Reduction/heatmap workers use 1 CPU/2 GB; matrix/PPDF/global plots use 1 CPU/4 GB.

Created: production config and frozen baseline; full source artifacts/manifest/provenance scaffolding; shared production helpers, run preparation/task metadata, reduction, aggregation, matrix-based PPDF, plots, incomplete-task diagnostics, full runtime/static validators; reduction/aggregation/full PPDF/full plot/heatmap Slurm workers; grid report and production runbook.

Changed: source-grid config; source/manifest generators; renderer and simulation worker for full-mode namespaces; `par_full.sh`; runtime full-mode routing; validation merge discovery to avoid recursively picking up production shards; pipeline documentation and this report. No GATE macro or detector-map edits.

Static checks: **PASS**. Python compilation passed for all 32 Python files checked (including nine provenance copies); `bash -n` passed for all 13 shell/Slurm files. Configuration JSON, source CSV/Parquet equality, grid coordinates/spacing/order, manifest/exposure/seed consistency, detector mapping dimensions, all ten frozen-file hashes, provenance copies/checksums, root propagation, resource preservation, reduction/matrix/PPDF architecture, dependency graph, resume diagnostics, and forbidden-pattern/reference-isolation checks passed. The dedicated full validator recorded 43 checks and zero failures in `results/validation/full/preparation_validation.json`. No runtime/event reduction or matrix generation was executed.

Actual validator outputs:

```text
MAGICCUBE CHUNK1 STATIC PREPARATION: PASS
MAGICCUBE FULL-FOV STATIC PREPARATION: PASS
```

Unresolved: exact paper endpoint convention awaits external confirmation; the production convention is explicit and configurable.

GATE executed: **NO**. Slurm submitted: **NO**. Full production runtime: **NOT RUN**.

Exact next manual launch:

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal/slurm"
bash par_full.sh
```

FULL-FOV PRODUCTION PREPARED — STOPPING BEFORE RUNTIME
