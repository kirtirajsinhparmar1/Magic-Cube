# Full-FOV grid decision

The single bounded evidence inspection found the 100 x 100 mm FOV and 2 mm sampling targets but did not establish exact endpoints. `../GateParallel_NewConfiguration/GATE-Macro/MAGIC_CUBE_V1_SPEC.md` (source-map section, approximately line 118) gives an approximate 50 x 50 estimate while explicitly deferring exact endpoints; the companion `magiccube_v1_config.json` records `exact_grid_endpoints_status: DEFERRED_TO_SOURCE_MAP_STEP`. The prior project configuration also left the endpoint policy unresolved. An approximate count is not an endpoint definition.

Production therefore uses the requested engineering fallback:

- `endpoint_mode: centered_inclusive`
- `endpoint_status: PROJECT_CONVENTION_PENDING_EXTERNAL_CONFIRMATION`
- x and y: -50, -48, ..., 0, ..., +48, +50 mm
- 51 x 51 = 2601 source positions, derived from configured extents and spacing
- z = -66 mm; detector front z = -16 mm; surface distance = 50 mm
- Point gamma source, 140 keV, isotropic, 3,700,000 Bq, 1 s/task
- One replicate/source by default

This is not a claim that the paper explicitly specifies 2601 positions. External confirmation of endpoints remains the only newly open scientific item.

`config/source_grid_config.json` is authoritative. Flat production fields are checked against the preserved nested/legacy aliases so validation-mode compatibility cannot silently diverge. The generator calculates axes and source count, rather than embedding a source count in processing code.

The actual artifacts are `config/full_source_positions.csv` and `.parquet`. Ordering is permanently y outer / x inner (x fastest), starting at (-50,-50), with contiguous source IDs. Matrix column j is the j-th row of that source table. For the frozen convention, the center is source 1300 and the final coordinate is (+50,+50).

`runtime/manifests/simulation_manifest_full.csv` contains one row per source/replicate. Task order is source outer / replicate inner. Seeds are `production_config.seed_base + task_id`; the configured default base is 1,000,001. Simulation and reduction array sizes derive from manifest row count, never separately maintained bounds.

Derived default scale: 2601 simulation/reduction tasks; 20,808 raw ROOT family shards (four Hits plus four Singles/task); 5,326,848 reduced detector/source entries; matrix shape (2048,2601). Each dense int64 raw or float64 response matrix contains 42,614,784 bytes of numeric data, excluding the small NPY header. No exact ROOT storage or runtime prediction is claimed.
