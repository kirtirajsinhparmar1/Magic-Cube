# OneCube visualization package

This is an isolated, static visualization layer for the already-working
OneCube pipeline. It uses the existing OneCube ROOT, PPDF, and system-matrix
products and does not change or rerun the scientific simulation.

The package covers:

`GATE ROOT Hits/Singles -> ROOT inspection -> geometry/setup figures -> hit projections -> cube intensity -> time/energy summaries -> dashboard -> optional cumulative animation -> validation report`

The scientific source of truth remains:

- `../config/onecube_config.json`
- `../runtime/merged/hits.root`
- `../runtime/merged/singles.root`
- `../results/ppdf/ppdf.csv`
- `../results/system_matrix/system_matrix.csv`
- `../results/system_matrix/system_matrix.npy`

The detector is one 2 x 2 x 2 mm GAGG cube, ID 0, centered at the origin. The
source is the configured 140 keV isotropic point source at `(0, 0, -51)` mm.

No visualization-only GATE macro is included: the existing Hits/Singles
products already contain the data needed for every requested static view and
for a truthful cumulative Hit buildup animation. No Slurm wrapper is needed;
all commands are explicit in `VISUALIZATION_RUNBOOK.md`.

Start with:

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube"
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/validate_visualization_preparation.py
```

Then follow `VISUALIZATION_RUNBOOK.md`.
