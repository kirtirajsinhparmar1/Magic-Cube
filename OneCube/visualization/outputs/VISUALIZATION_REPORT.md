# OneCube visualization report

## Scope

This package visualizes the already-working OneCube end-to-end result. It does
not change or rerun the scientific setup. The detector is one 2 x
2 x 2 mm `GAGG` cube with canonical
detector ID `0`. The source is `gamma` at
140 keV, `(0, 0, -51)` mm, with a
50-mm source-to-surface distance.

## Generated visualizations

- `geometry_overview.png`: exact configuration sketch of world, source, cube, and +z direction.
- `detector_render.png`: exact configuration rendered as a static 3D scene.
- `hits_3d.png`: exact Hits `posX/posY/posZ` positions and cube bounds.
- `hits_projection_xy.png`, `hits_projection_xz.png`, `hits_projection_yz.png`: derived 2D projections of Hits positions.
- `cube_intensity_3d.png` and `cube_intensity_xy/xz/yz.png`: derived voxel aggregation using `deposited energy branch edep [MeV]`.
- `time_energy_summaries.png` and branch-specific histogram PNGs: exact ROOT branch distributions; event-count histograms are derived from event IDs.
- `singles_summary.png`: exact Singles count, energy, and time summaries.
- `response_dashboard.png`: compact view of setup, counts, existing PPDF, and existing system-matrix response.
- `hit_buildup.gif`: Generated: `/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/visualization/outputs/hit_buildup.gif` (ascending time branch; cumulative positions, not trajectories).

## Data provenance

Exact data products used:

- Hits: `/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/merged/hits.root`, tree `tree`, `233` entries.
- Singles: `/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/merged/singles.root`, tree `tree`, `233` entries.
- PPDF: `results/ppdf/ppdf.csv`, row count `1`; ppdf `1.0`.
- System matrix: `results/system_matrix/system_matrix.csv` and `.npy`; response `62.972972972972975 cps/MBq`.
- Existing Gate runtime status file: `/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube/runtime/sim/gate_exit_code.txt`; recorded exit code `0`.

Derived/aggregated products:

- Hit projections, voxel occupancy/deposited-energy intensity, histograms, and dashboard annotations.
- No native volume ID was used as detector identity; the visualization contract assigns canonical detector ID `0`.
- No photon trajectory was reconstructed.

## Singles position limitation

Available from exact branches `globalPosX,globalPosY,globalPosZ`; position PNG generated.

## Animation limitation

`trajectory_data_present` is `False`. The animation, when present, is cumulative Hit buildup ordered by measured time or ROOT entry order; it is not a physical photon track.

## Validation

- Output validation status at report creation: `PASS`.
- Required static PNGs and supported optional outputs are checked by `scripts/validate_visualization_outputs.py`.
- This visualization package does not execute Gate, submit Slurm jobs, or modify the production OneCube pipeline.

## Manual commands

```bash
cd "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/OneCube"
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/validate_visualization_preparation.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/inspect_onecube_root.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_geometry_overview.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_detector_render.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_hits_3d.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_hits_projections.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_cube_intensity.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_time_energy_summaries.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_singles_summary.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/plot_response_dashboard.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/make_hit_animation.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/validate_visualization_outputs.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/final_visualization_summary.py
env -u PYTHONPATH /user/kmparmar/venv/bin/python visualization/scripts/validate_visualization_outputs.py --require-report
```

The final successful output validator classification is:

`ONECUBE VISUALIZATION OUTPUT VALIDATION: PASS`
