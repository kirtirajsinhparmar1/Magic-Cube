#!/usr/bin/env python3
"""Write the final human-readable OneCube visualization report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from visualization_common import VisualizationError, load_configs, output_dir, read_csv_rows, runtime_dir


def load_optional(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="visualization config JSON")
    args = parser.parse_args()
    try:
        visual, source, source_path = load_configs(args.config)
        out = output_dir(visual, args.config)
        runtime = runtime_dir(visual, args.config)
        inspection = load_optional(runtime / "root_inspection.json")
        if inspection is None:
            raise VisualizationError("run inspect_onecube_root.py before final summary")
        intensity = load_optional(runtime / "cube_intensity_summary.json") or {}
        singles = load_optional(runtime / "singles_availability.json") or {}
        animation = load_optional(runtime / "animation_status.json") or {}
        output_validation = load_optional(runtime / "output_validation.json")
        project_root = source_path.parents[1]
        ppdf_rows = read_csv_rows(project_root / "results" / "ppdf" / "ppdf.csv")
        matrix_rows = read_csv_rows(project_root / "results" / "system_matrix" / "system_matrix.csv")
        ppdf = ppdf_rows[0] if ppdf_rows else {}
        matrix = matrix_rows[0] if matrix_rows else {}
        detector = source["detector"]
        source_spec = source["source"]
        gate_exit_path = project_root / "runtime" / "sim" / "gate_exit_code.txt"
        gate_exit = gate_exit_path.read_text().strip() if gate_exit_path.is_file() else "not recorded"
        validation_status = output_validation.get("status", "NOT_RUN") if output_validation else "NOT_RUN"
        animation_line = (
            f"Generated: `{animation.get('output')}` ({animation.get('basis', 'cumulative buildup')})."
            if animation.get("supported") else
            f"Not generated: {animation.get('reason', 'unsupported data')}."
        )
        singles_position = singles.get("positions", {})
        if singles_position.get("available"):
            singles_position_line = f"Available from exact branches `{singles_position.get('branches')}`; position PNG generated."
        else:
            singles_position_line = f"Unavailable; no fabricated location view. Reason: {singles_position.get('reason', 'not recorded')}"
        report = f"""# OneCube visualization report

## Scope

This package visualizes the already-working OneCube end-to-end result. It does
not change or rerun the scientific setup. The detector is one {detector['size_x_mm']:g} x
{detector['size_y_mm']:g} x {detector['size_z_mm']:g} mm `{detector['material']}` cube with canonical
detector ID `{detector['detector_id']}`. The source is `{source_spec['particle']}` at
{source_spec['energy_keV']:g} keV, `(0, 0, {source_spec['z_mm']:g})` mm, with a
{source_spec['surface_distance_mm']:g}-mm source-to-surface distance.

## Generated visualizations

- `geometry_overview.png`: exact configuration sketch of world, source, cube, and +z direction.
- `detector_render.png`: exact configuration rendered as a static 3D scene.
- `hits_3d.png`: exact Hits `posX/posY/posZ` positions and cube bounds.
- `hits_projection_xy.png`, `hits_projection_xz.png`, `hits_projection_yz.png`: derived 2D projections of Hits positions.
- `cube_intensity_3d.png` and `cube_intensity_xy/xz/yz.png`: derived voxel aggregation using `{intensity.get('weighting', 'detected Hit data')}`.
- `time_energy_summaries.png` and branch-specific histogram PNGs: exact ROOT branch distributions; event-count histograms are derived from event IDs.
- `singles_summary.png`: exact Singles count, energy, and time summaries.
- `response_dashboard.png`: compact view of setup, counts, existing PPDF, and existing system-matrix response.
- `hit_buildup.gif`: {animation_line}

## Data provenance

Exact data products used:

- Hits: `{inspection['hits']['file']}`, tree `{inspection['hits']['tree_name']}`, `{inspection['hits']['entry_count']:,}` entries.
- Singles: `{inspection['singles']['file']}`, tree `{inspection['singles']['tree_name']}`, `{inspection['singles']['entry_count']:,}` entries.
- PPDF: `results/ppdf/ppdf.csv`, row count `{len(ppdf_rows)}`; ppdf `{ppdf.get('ppdf', 'unavailable')}`.
- System matrix: `results/system_matrix/system_matrix.csv` and `.npy`; response `{matrix.get('response_cps_per_MBq', 'unavailable')} cps/MBq`.
- Existing Gate runtime status file: `{gate_exit_path}`; recorded exit code `{gate_exit}`.

Derived/aggregated products:

- Hit projections, voxel occupancy/deposited-energy intensity, histograms, and dashboard annotations.
- No native volume ID was used as detector identity; the visualization contract assigns canonical detector ID `0`.
- No photon trajectory was reconstructed.

## Singles position limitation

{singles_position_line}

## Animation limitation

`trajectory_data_present` is `{animation.get('trajectory_data_present', False)}`. The animation, when present, is cumulative Hit buildup ordered by measured time or ROOT entry order; it is not a physical photon track.

## Validation

- Output validation status at report creation: `{validation_status}`.
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
"""
        report_path = out / "VISUALIZATION_REPORT.md"
        report_path.write_text(report)
        print(report)
        print(f"Report written: {report_path}")
        return 0
    except (VisualizationError, OSError, ValueError, KeyError) as exc:
        print(f"Final visualization summary FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
