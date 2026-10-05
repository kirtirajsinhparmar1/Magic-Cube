# Chunk 1 build report

MagicCubeFinal contains an isolated full-detector GATE configuration, deterministic detector/source artifacts, manifest-driven simulation preparation, source-preserving postprocessing, PPDF and absolute system-matrix generation, plotting, Slurm orchestration, and static/runtime validators. No GATE or scheduler command is part of Chunk 1 validation. The authoritative static result is printed by `scripts/validate_preparation.py`; runtime remains intentionally not run.

Reference trees were read only. Initial critical OneCube macro hashes are recorded in `config/reference_baseline.json` and verified by the preparation validator.
