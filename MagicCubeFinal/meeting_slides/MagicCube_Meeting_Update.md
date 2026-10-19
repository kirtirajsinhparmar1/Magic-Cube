# MagicCube meeting update

A meeting-ready progress deck from OneCube to full MagicCube.

## Evidence boundary

- OneCube and the MagicCube 2048×1 result use existing validated outputs.
- The full-FOV run is shown only through completion markers. The final 2048×2601 matrix is not present and is not claimed as complete.
- The geometry figures use the frozen MagicCube configuration and canonical detector map.

## 1. Title / objective

Goal: reproduce the Magic-Cube self-collimating gamma camera in GATE/mcsim. Progression: OneCube → MagicCube → full-FOV production.

**Data status:** Configuration and project status.

![Slide 01](slides/slide_01_title.png)

## 2. OneCube motivation

One 2×2×2 mm GAGG cube plus a 140 keV point source provides the smallest useful proof that the transport-to-matrix pipeline works.

**Data status:** Validated OneCube geometry and source configuration.

![Slide 02](slides/slide_02_onecube_motivation.png)

## 3. OneCube end-to-end pipeline

Source → GATE → Hits → Singles → PPDF → 1×1 system matrix. PASS: 233 Hits, 233 Singles, ppdf=1.0.

**Data status:** OneCube final_validation.json, system_matrix.csv, ppdf.csv.

![Slide 03](slides/slide_03_onecube_pipeline.png)

## 4. OneCube visual results

Geometry, Hits/Singles positions, and response dashboard are copied from existing OneCube visualization outputs.

**Data status:** Existing OneCube PNG outputs.

![Slide 04](slides/slide_04_onecube_results.png)

## 5. Transition to full MagicCube

Scale to 2048 GAGG + 2048 K9 over 16 layers while preserving the same pipeline.

**Data status:** Frozen magiccube_config.json.

![Slide 05](slides/slide_05_transition.png)

## 6. Full MagicCube geometry

Clean 3D render of the 16×16×16 checkerboard lattice with GAGG/K9 roles, source-facing side, axes, and dimensions.

**Data status:** Frozen configuration plus detector_map.csv.

![Slide 06](slides/slide_06_geometry.png)

## 7. Layer / checkerboard structure

Representative depth layers show the phase-alternating GAGG/K9 checkerboard that makes self-collimation testable.

**Data status:** Frozen material rule (ix+iy+k) mod 2.

![Slide 07](slides/slide_07_layers.png)

## 8. Validated MagicCube single-source runtime

Validated 2048×1 run: 189,964 Hits, 189,844 Singles, complete 2048-vector, and MAGICCUBE_2048x1_END_TO_END_PASS.

**Data status:** final_summary_validation.json, runtime_validation_validation.json, merge_summary.json, raw system matrix.

![Slide 08](slides/slide_08_validated_runtime.png)

## 9. Validated detector response

Actual Singles counts color all 2048 canonical GAGG positions for the validated point source.

**Data status:** system_matrix_raw.npy plus detector_map.csv.

![Slide 09](slides/slide_09_detector_response.png)

## 10. Layer / depth response

Actual validated Singles counts aggregated by physical layer k, with representative layer heatmaps.

**Data status:** system_matrix_raw.npy plus detector_map.csv.

![Slide 10](slides/slide_10_layer_response.png)

## 11. Full-FOV production architecture

2,601 source positions each produce a 2048-element vector; columns assemble into a 2048×2,601 matrix.

**Data status:** source_grid_config.json and production architecture.

![Slide 11](slides/slide_11_full_fov_architecture.png)

## 12. Current full-FOV run progress

Marker snapshot: exit 0=1978, exit 1=615, running=8. PARTIAL PRODUCTION — NOT FINAL SCIENTIFIC RESULT.

**Data status:** runtime/merged/full/task_*.exit_code.txt markers only; no final matrix values.

![Slide 12](slides/slide_12_full_fov_progress.png)

## 13. Current status / next steps

OneCube, geometry, Hits/Singles, mapping, and 2048×1 validation are complete. Full-FOV production is ongoing; next steps are comparison, assumptions validation, final matrix, and reconstruction.

**Data status:** Mixed validated and partial-production status.

![Slide 13](slides/slide_13_status.png)
