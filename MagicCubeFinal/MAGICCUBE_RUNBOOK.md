# Runbook

All commands start from the isolated project.

## Chunk 1 static validation

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal"
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/validate_preparation.py
```

## Chunk 2: full detector x one source

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal/slurm"
bash par_validation.sh
```

The orchestrator prints parseable job IDs. Monitor manually with `squeue -j <job_ids>` and inspect `../runtime/logs/`. After dependencies finish:

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal"
env -u PYTHONPATH /user/kmparmar/venv/bin/python scripts/validate_runtime.py --mode validation
```

The required success token is `MAGICCUBE_2048x1_END_TO_END_PASS`.

## Later full production

First set an explicit `endpoint_mode` in `config/source_grid_config.json`, then:

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/MagicCubeFinal/slurm"
bash par_full.sh
```

No worker submits nested jobs; only the two orchestrators call `sbatch --parsable` and wire `afterok` dependencies.
