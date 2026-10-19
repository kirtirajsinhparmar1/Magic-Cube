# OneCube Imaging Pipeline Results

## Status

**SOFTWARE PIPELINE READY. SCIENTIFIC RECONSTRUCTION IDENTIFIABLE: NO.**

The reusable response-analysis, phantom, forward-projection, MLEM, metrics, plotting, and validation code runs against the validated OneCube artifacts. The current response contains one measurement row and one source voxel, so its scalar MLEM result is a calibration smoke result, not a spatial image reconstruction.

## Reference methodology and OneCube mapping

Only the downstream algorithms were consulted in the [reference SPECT repository](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT):

| Reference calculation | Mathematical operation | OneCube input |
| --- | --- | --- |
| PPDF / response interpretation | Treat response samples as spatially indexed system response values and retain their measurement/source ordering. | `results/system_matrix/system_matrix.npy`, its metadata and CSV; the matrix stores absolute response in counts/(s Bq). OneCube has no sampled spatial PPDF beyond its one source position. |
| Beam/response region | Threshold each response relative to its own measured peak and use the associated coordinates to describe the response region and direction. | Matrix row, source coordinates, detector coordinates, configured relative threshold. No reference boundary or scanner geometry is used. |
| Sensitivity | For each voxel `j`, `S_j = sum_i A_rate[i,j]`. | The OneCube rate response matrix; outputs are cps/Bq and, when converted, cps/MBq. |
| FWHM | Find the peak, use the half-maximum crossings, and interpolate between sampled coordinates. | OneCube response by source coordinate. One spatial sample cannot supply either crossing. |
| ASCI | Mark voxels covered by each valid response in its measured angular bin; divide occupied bins by configured angular bins. | Directions inferred from OneCube detector positions and response-weighted source coordinates in the configured x-z plane. |
| JI | `JI = (mean sensitivity / mean FWHM^2) * (ASCI_percent / 100)`. | OneCube mean sensitivity, valid OneCube FWHM values, and OneCube ASCI. JI is left undefined when there is no valid FWHM. |
| Phantom and projection | Flatten the phantom in system-matrix voxel order and multiply by the system response. | Configured synthetic phantom on the existing OneCube source columns; `y_expected = A_counts @ x_true`. |
| MLEM | Repeated forward projection, data/prediction ratio, transpose backprojection, and sensitivity-normalized nonnegative update. | Generic measurement-by-voxel projection operator and count vector. |

Reference method locations: [beam extraction](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/arg_extract_beam_masks.py), [beam properties/FWHM](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/beam_property_extract.py), [ASCI](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/asci_plot_generation.py), [JI](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/6_calc_ji.py), [forward projection](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/projection_t8.py), and [MLEM](https://github.com/kirtirajsinhparmar1/Small-Animal-Imaging-SPECT/blob/main/mlem_torch_gpf_nonmpi.py). These were used to understand algorithms only.

## Geometry isolation

No reference detector geometry, detector dimensions, scanner architecture, plate or attenuation model, transforms, source positions, FOV dimensions, camera distances, or geometry-generation code was copied. The existing OneCube GATE setup and outputs remain authoritative and were not modified.

## System response and sensitivity

The matrix convention is unambiguous: `A_rate[i,j]`, where `i` is a measurement bin and `j` is a source/image voxel. Detector ID, acquisition-view ID, and measurement-bin ID are separate row maps; the current OneCube source table has one row, detector 0, and no explicit acquisition-view identifier. Source IDs and xyz coordinates preserve matrix column order.

The stored response is `6.2972973e-05 cps/Bq`, or **62.972973 cps/MBq**. Since the acquisition duration is 1 s, the count projection operator is numerically the same and has units counts/Bq. The separate original raw calibration observation is **233 Singles** at 3.7 MBq for 1 s; it is retained as raw count data and is not presented as a spatial sensitivity value. With one voxel, central, mean, minimum, and maximum sensitivity are all equal to the value above.

## Beam analysis, FWHM, ASCI, and JI

Response-region masking is relative to each measurement row's measured peak; the configured threshold is 0.01. The current nonzero sample is inside the derived response region. Its direction is inferred as **270°** in the configured x-z plane.

FWHM uses the marginal spatial profile along the configured x axis, requires at least three distinct spatial samples, and linearly interpolates both half-height crossings. The current profile has one coordinate, so **0 of 1 FWHM values are valid**. The output stores the peak, profile, beam/measurement metadata, validity flag, and reason instead of assigning a width.

ASCI uses 360 configured angular bins. The only measured response occupies **1/360 bins**, so the only voxel has ASCI **0.0027778 as a fraction, or 0.277778%**. This records the available angular coverage and does not imply sufficient tomography.

The verified reference formula is `JI = (mean_sensitivity_cps_per_bq / mean_fwhm_mm^2) * (mean_asci_percent / 100)`. Inputs recorded are mean sensitivity `6.2972973e-05 cps/Bq`, mean FWHM `null` (no valid profiles), and mean ASCI `0.277778%`. JI is therefore **null / not scientifically computable**.

## Phantom, forward projection, and MLEM

The configurable phantom framework supports uniform, single-voxel, and Gaussian patterns on the existing source-coordinate order. The current synthetic software-check phantom is uniform on its single voxel and totals **3.7 MBq**. It is not measured phantom data.

For count projection, `A_counts = A_rate * acquisition_s` and `y_expected = A_counts @ x_true`. The current noiseless result is **233 expected counts**. Deterministic Poisson sampling with seed `1402026` produced **242 counts**. Both arrays and their units, seed, and provenance are retained.

MLEM uses positive initialization, the configured epsilon, safe zero-prediction handling, precomputed `A.T @ 1`, nonnegative updates, and a full vector for every configured iteration. The 40-iteration scalar smoke result is **3.842918 MBq**. On this generated Poisson sample, MSE is `2.0425685e10 Bq^2`, RMSE is `142918.45 Bq`, normalized error is `0.0386266`, and activity recovery is `1.0386266`; correlation is null because a one-element vector has no defined correlation. These figures demonstrate software execution only and are not spatial reconstruction performance.

Optional Gaussian post-filtering is disabled by default, operates separately from raw MLEM, and is recorded separately if enabled.

## Plots and quantitative outputs

The run creates source/image-grid, sensitivity, spatial-response, detector-response, response-region, response-profile/FWHM, ASCI, phantom, forward-projection comparison, raw reconstruction, reconstruction error, side-by-side phantom/reconstruction/error, and MLEM convergence figures. Numeric outputs include response operators, sensitivity vectors/maps and summaries, response masks, FWHM records, ASCI occupancy and map, JI, phantom vectors/images, noiseless/noisy projections, iteration estimates/history, and reconstruction metrics.

## Scientific limitation and acquisition requirement

Current OneCube data have **1 measurement bin, 1 voxel, rank 1, and 1 occupied angular bin**. The software validator reports **SOFTWARE PIPELINE READY** and **SCIENTIFIC RECONSTRUCTION IDENTIFIABLE: NO**. The scalar result must not be interpreted as a reconstructed image.

An identifiable spatial reconstruction needs the intended multi-voxel image grid populated by OneCube response measurements, plus enough independent measurement rows/views to give `rank(A) = number_of_voxels` (therefore at least as many rows as voxels) and genuine angular coverage across distinct measured acquisition directions. The present artifact has no second voxel or second angular view. The minimum checks in the config require two spatial voxels and two distinct angular bins; real imaging should use a sufficiently sampled image grid and angular set for the intended resolution.

## MagicCubeFinal transferability

The generic modules under `analysis/`, `reconstruction/`, and the imaging plotting code can transfer directly: sensitivity, response masks, interpolated FWHM, ASCI occupancy, the verified JI formula, phantom generation, forward projection, MLEM, metrics, and validation. For MagicCubeFinal, replace only the input adapter/configuration with its detector map, ordered source grid, measurement/view map, system response and acquisition metadata. Confirm row/column order and units before running; no OneCube geometry assumptions are part of the generic calculations.

## Validation and runtime

The static compile check passed. The downstream pipeline and validator passed all software checks, including dimensions, ordering, finite/nonnegative values, response masks, explicit FWHM/JI definedness, ASCI range, phantom/projection/reconstruction shapes, all 40 MLEM iterations, generated plots, provenance/config, and an independent two-voxel identity-matrix forward-projection/MLEM smoke case. The validator correctly reports the scientific identifiability check as false and writes the acquisition requirement to `results/imaging/validation/imaging_validation.json`.

Gate executed: **NO**. Slurm submitted: **NO**.

