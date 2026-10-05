# Pipeline

`source positions -> simulation manifest -> rendered GATE task -> ROOT Hits/Singles -> source-preserving merge index -> canonical position mapping -> PPDF + absolute system matrix -> plots -> validation`

Validation mode contains one source and one replicate and must yield a `(2048,1)` matrix. Full mode consumes the configured source table and yields `(2048,N_sources)`. Each simulation array index selects exactly one manifest row. Replicates never erase source identity: downstream counts are summed for identical detector/source conditions.

Singles are quantitative; Hits are diagnostic. Raw counts remain in long tables and `system_matrix_raw_counts.npy`. Absolute response is `n_ij/(T_j*A_j)` in cps/Bq and is also reported in cps/MBq. Detector-conditioned PPDF is `n_ij/sum_j(n_ij)`; zero denominators produce explicit zeros, never NaN.

## Full-FOV production

The event-level merge above is the preserved one-source validation path. Full production instead uses `raw ROOT -> per-source 2048-vector -> aggregate matrix -> PPDF -> global plots + detector heatmap array -> full validation`. There is no global event CSV for full mode. All eight ROOT family shards/task remain authoritative event evidence.

`config/full_source_positions.csv` defines matrix-column order. `runtime/manifests/simulation_manifest_full.csv` defines both simulation and reduction arrays. Compact vectors retain every detector, including zeros, and preserve source/replicate/seed/exposure metadata. Replicate counts and live times are summed per source. Production raw and absolute matrices are `results/system_matrix/full/system_matrix_raw.npy` and `system_matrix.npy`; PPDF is computed directly from raw counts. Long-format Parquet is written in bounded source-sized row groups.

The direct `par_full.sh` orchestrator exports the real project root to workers, applies one configured concurrency ceiling, and submits all dependencies. Input snapshots/checksums and task metadata prevent incompatible reductions from mixing. `find_incomplete_tasks.py` only diagnoses missing/failed work; it never resubmits. See `FULL_FOV_GRID_REPORT.md` and `FULL_PRODUCTION_RUNBOOK.md` for the frozen grid policy and manual launch.
