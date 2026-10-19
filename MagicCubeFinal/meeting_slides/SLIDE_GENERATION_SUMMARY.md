# Slide generation summary

Generated: 2026-09-28T10:20:36-04:00

## Scope and safety

- All generated artifacts are under `MagicCubeFinal/meeting_slides/`.
- Gate executed: **NO**.
- Slurm submitted: **NO**.
- Current production jobs stopped: **NO**.
- Simulation code, configuration, detector map, GATE macros, Slurm scripts, runtime data, and production jobs were not modified by this generation step.
- The full-FOV final matrix is not present; it is not claimed complete.

## Data provenance

### Validated data used

- OneCube: `OneCube/results/validation/final_validation.json`, `OneCube/results/system_matrix/system_matrix.csv`, `OneCube/results/ppdf/ppdf.csv`, and existing visualization PNGs.
- MagicCube single-source: `MagicCubeFinal/results/final_summary_validation.json`, `results/validation/runtime_validation_validation.json`, `runtime/merged/merge_summary.json`, `results/system_matrix/system_matrix_raw.npy`, `results/system_matrix/system_matrix.npy`, and `config/detector_map.csv`.
- Geometry / source grid: frozen `config/magiccube_config.json` and `config/source_grid_config.json`.

### Partial production data used

- Slide 12 uses only existing `runtime/sim/full/task_*.exit_code.txt` completion markers.
- Marker snapshot at generation time: exit 0 completed = **1978**, exit 1 = **615**, RUNNING = **8**, total marker files = **2601**.
- Because failed/running tasks and the absent assembled matrix remain, the slide is labeled **PARTIAL PRODUCTION — NOT FINAL SCIENTIFIC RESULT**.

## Slide status

| Slides | Status |
|---|---|
| 1–7 | Project objective, validated OneCube evidence, frozen geometry/configuration, and structural illustrations |
| 8–10 | **Validated MagicCube 2048×1 data** |
| 11 | Architecture / target-shape explanation |
| 12 | **Partial production markers only** |
| 13 | Mixed completed + partial status and next steps |

## Generated artifacts

- `MagicCube_Meeting_Update.md` — 3,915 bytes
- `MagicCube_Meeting_Update.pptx` — 3,092,556 bytes
- `__pycache__/generate_meeting_slides.cpython-310.pyc` — 38,351 bytes
- `figures/full_fov_architecture.png` — 77,024 bytes
- `figures/full_fov_progress.png` — 53,801 bytes
- `figures/layer_checkerboard_exploded.png` — 56,646 bytes
- `figures/magiccube_geometry_3d.png` — 564,381 bytes
- `figures/magiccube_heatmap_existing.png` — 70,895 bytes
- `figures/magiccube_positions_existing.png` — 632,382 bytes
- `figures/magiccube_scaling.png` — 54,082 bytes
- `figures/onecube_geometry_existing.png` — 248,984 bytes
- `figures/onecube_hits_existing.png` — 537,997 bytes
- `figures/onecube_pipeline.png` — 58,592 bytes
- `figures/onecube_response_dashboard_existing.png` — 186,961 bytes
- `figures/onecube_singles_existing.png` — 427,264 bytes
- `figures/validated_detector_response.png` — 481,762 bytes
- `figures/validated_layer_response.png` — 78,717 bytes
- `generate_meeting_slides.py` — 41,980 bytes
- `slides/slide_01_title.png` — 112,489 bytes
- `slides/slide_02_onecube_motivation.png` — 229,817 bytes
- `slides/slide_03_onecube_pipeline.png` — 136,515 bytes
- `slides/slide_04_onecube_results.png` — 374,542 bytes
- `slides/slide_05_transition.png` — 149,213 bytes
- `slides/slide_06_geometry.png` — 591,757 bytes
- `slides/slide_07_layers.png` — 211,675 bytes
- `slides/slide_08_validated_runtime.png` — 141,529 bytes
- `slides/slide_09_detector_response.png` — 582,786 bytes
- `slides/slide_10_layer_response.png` — 199,380 bytes
- `slides/slide_11_full_fov_architecture.png` — 167,789 bytes
- `slides/slide_12_full_fov_progress.png` — 161,109 bytes
- `slides/slide_13_status.png` — 200,945 bytes

## Verification intent

- PNGs are checked for existence and non-zero size after generation.
- The PPTX is checked as a readable ZIP package containing 13 slide XML parts and 13 slide PNG media parts.
- The Markdown backup is checked for existence and non-zero size.
- No Gate or Slurm command is invoked by `generate_meeting_slides.py`.
