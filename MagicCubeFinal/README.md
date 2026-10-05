# MagicCubeFinal

This isolated project prepares the final Magic-Cube SPECT simulation and analysis architecture. It generalizes the proven `OneCube` software pipeline while reusing the validated eight-family full-detector geometry from the original research tree. `OneCube` and every pre-existing mcsim directory are read-only references; all generated macros, logs, ROOT files, tables, matrices, and plots remain below this directory.

The prepared workflow is: manifest-driven GATE simulation, source-preserving merge/indexing, ROOT inspection, all-detector PPDF generation, absolute system-matrix generation, scientific plots, and runtime validation. Chunk 1 performs static preparation only. The first runtime milestone is the complete 2048-sensitive-detector geometry with the single on-axis source.

Start with `env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/validate_preparation.py`. Runtime instructions are in `MAGICCUBE_RUNBOOK.md`.
