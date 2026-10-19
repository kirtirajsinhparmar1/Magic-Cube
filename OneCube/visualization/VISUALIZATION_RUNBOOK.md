# OneCube visualization runbook

Run these commands manually from the OneCube project. They read the existing
OneCube runtime/results products. They do not execute Gate and do not submit
Slurm work.

## 1. Static preparation check

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube"
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/validate_visualization_preparation.py
```

Expected result:

```text
ONECUBE VISUALIZATION STATIC PREPARATION: PASS
```

## 2. Inspect both ROOT products

```bash
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/inspect_onecube_root.py
```

This writes `visualization/runtime/root_inspection.json` and reports the
discovered tree names, entries, branches, dtypes, positions, energy, time, and
event identity fields.

## 3. Generate the visualizations in dependency order

```bash
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_geometry_overview.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_detector_render.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_hits_3d.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_hits_projections.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_cube_intensity.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_time_energy_summaries.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_singles_summary.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_response_dashboard.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/make_hit_animation.py
```

The static PNGs and optional GIF are written only below
`visualization/outputs/`. Availability records and intensity metadata are
written below `visualization/runtime/`.

## 4. Validate generated outputs and write the report

The first validation pass checks all generated figures and writes an
intermediate machine-readable result:

```bash
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/validate_visualization_outputs.py
```

Then write the human-readable report:

```bash
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/final_visualization_summary.py
```

Finally require that the report itself is present and rerun the authoritative
output check:

```bash
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/validate_visualization_outputs.py --require-report
```

Expected final result:

```text
ONECUBE VISUALIZATION OUTPUT VALIDATION: PASS
```

## 5. Individual-stage debugging commands

If one visualization needs to be regenerated, rerun only its command from
section 3. A ROOT-dependent plot requires a successful prior
`inspect_onecube_root.py`; the dashboard requires that inspection plus the
existing PPDF/system-matrix CSV products. The output validator prints the
concrete missing or invalid artifact and never turns an unavailable plot into
a fabricated success.

## 6. Input and output map

| Stage | Inputs | Outputs |
| --- | --- | --- |
| ROOT inspection | `runtime/merged/hits.root`, `runtime/merged/singles.root` (merged candidates first) | `visualization/runtime/root_inspection.json` |
| Geometry | `config/onecube_config.json` | `outputs/geometry_overview.png`, `outputs/detector_render.png` |
| Hits views | Hits ROOT and config | `outputs/hits_3d.png`, three projection PNGs |
| Cube intensity | Hits ROOT and config | one 3D PNG, three slice PNGs, `runtime/cube_intensity_summary.json` |
| Time/energy | Hits and Singles ROOT | summary PNGs, `runtime/time_energy_availability.json` |
| Singles | Singles ROOT and config | `outputs/singles_summary.png`, optional position PNG, availability JSON |
| Dashboard | ROOT inspection, `results/ppdf/ppdf.csv`, `results/system_matrix/system_matrix.csv` | `outputs/response_dashboard.png` |
| Animation | Hits ROOT positions and optional time | `outputs/hit_buildup.gif` or explicit unavailable JSON |
| Final validation | all outputs and existing data products | `runtime/output_validation.json` |
| Final report | validation/inspection summaries and existing products | `outputs/VISUALIZATION_REPORT.md` |

## 7. Scientific limitations

This is a visualization package for one detector and one source. It does not
validate the full Magic-Cube geometry, reconstruct images, infer photon tracks,
or claim detector performance beyond what the existing OneCube products show.
