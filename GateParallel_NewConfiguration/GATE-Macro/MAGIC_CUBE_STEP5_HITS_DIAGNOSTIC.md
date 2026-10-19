# Magic-Cube Step-5 Raw-Hits Diagnostic

## 1. Reason for Diagnostic

The authoritative production-system runtime was job `26040149` on GATE 9.4
with Geant4 11.2.1. It exited with code 0: the centered cylindricalPET
wrapper and system registration parsed, initialization and acquisition
completed, and no fatal SpatialResolution exception occurred. However, the
Hits and Singles ROOT collections both contained zero entries. A real
detector pulse was therefore not demonstrated.

This bounded diagnostic isolates raw Hits before re-enabling the digitizer.

## 2. What Job 26040149 Proved

The run proved that:

- the `cylindricalPET` wrapper volume was accepted;
- the cylindricalPET system registration was accepted;
- all four `attachCrystalSD` commands were accepted;
- geometry and PhotoElectric physics initialization passed;
- the source initialized and acquisition completed;
- there was no `COMMAND NOT FOUND` failure;
- there was no `GateSpatialResolution` system-lookup failure.

It did not prove that a detector interaction reached a GAGG sensitive volume.

## 3. Diagnostic Strategy

Two Hits-only macros reuse the frozen production geometry, production system,
and production physics. Both omit the digitizer and Singles output entirely.

Test A generates four short, internal 30-keV gamma probes, one at the first
known GAGG center of each active family. Test B reuses the validated external
140-keV point/isotropic smoke source at `(0, 0, -66) mm`. The job runs Test A
then Test B sequentially and keeps their logs, exit codes, and ROOT prefixes
separate.

## 4. Test A — Internal GAGG Probe

Macro: `magiccube_step5_hits_internal.mac`

Configuration reused from the Step-4 runtime probe setup:

| Family | Global center (mm) |
|---|---:|
| `mc_gagg_ee` | `(-31.5, -31.5, -15.0)` |
| `mc_gagg_eo` | `(-31.5, -27.3, -13.0)` |
| `mc_gagg_oe` | `(-27.3, -31.5, -13.0)` |
| `mc_gagg_oo` | `(-27.3, -27.3, -15.0)` |

Each source is a point, isotropic gamma source at 30 keV and 100 Bq. The
acquisition is one second. Hits are enabled under the output prefix
`magiccube_step5_hits_internal`; Singles and all digitizer commands are
absent.

## 5. Test B — External 140-keV Smoke

Macro: `magiccube_step5_hits_external.mac`

The source is the same bounded external smoke configuration used by the
Step-4/runtime smoke setup: a point, isotropic gamma source at 140 keV,
position `(0, 0, -66) mm`, activity 20,000 Bq, and a one-second acquisition.
Hits are enabled under the separate prefix `magiccube_step5_hits_external`.

## 6. Frozen Production Components

The following existing files are reused unchanged:

- `magiccube_production_geometry.mac`
- `magiccube_production_system.mac`
- `magiccube_production_physics.mac`
- `detector_map.csv`

No wrapper dimensions, system hierarchy, sensitive-detector attachment,
physics, material, placement, repeater, or detector-ID contract is changed.

## 7. Digitizer Exclusion

`magiccube_production_digitizer.mac` is intentionally not executed. There are
no Singles, Adder, energy-resolution, spatial-resolution, or energy-framing
commands in either diagnostic. This task tests only whether the current
production sensitive-detector path can create raw Hits.

## 8. Acceptance Criteria

Each test independently requires:

- Gate exit code 0;
- no fatal/abort or system-lookup error in its log;
- at least one relevant Hits ROOT file;
- readable, non-empty Hits content when the Python ROOT environment permits
  inspection.

The optional internal position check uses `detector_map.csv` and reports
whether readable hit positions map with zero unmapped and zero ambiguous
observations. A Python/NumPy/uproot environment error is reported separately
and is not reclassified as a Gate failure.

## 9. Interpretation Matrix

| Internal Hits | External Hits | Interpretation |
|---:|---:|---|
| >0 | >0 | `RAW_HITS_PATH_VALIDATED` |
| >0 | 0 | `INTERNAL_PASS_EXTERNAL_FAIL` |
| 0 | 0 | `PRODUCTION_SD_NOT_PRODUCING_HITS` |
| 0 | >0 | `DIAGNOSTIC_INCONSISTENCY` |

## 10. Status

**PREPARED — RUNTIME NOT YET VALIDATED**

Codex did not execute Gate or submit Slurm. The user must run the single
bounded job manually from the CCR environment.
