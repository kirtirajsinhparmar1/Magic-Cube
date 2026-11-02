#!/usr/bin/env python3
"""Append verified production results to the single primary project report."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict[str, Any]:
    path = PROJECT_ROOT / relative
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "not defined"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def _runtime_section() -> str:
    reduction = _load("runtime/provenance/calibration_reduction.json")
    system = _load("runtime/provenance/system_analysis.json")
    reconstruction = _load("runtime/provenance/reconstruction.json")
    validation = _load("results/validation/runtime_validation.json")
    sensitivity = _load("results/sensitivity/sensitivity_summary.json")
    fwhm = _load("results/fwhm/fwhm_summary.json")
    asci = _load("results/asci/asci_applicability.json")
    ji = _load("results/asci/ji_result.json")
    diagnostics = _load("results/system_matrix/information_diagnostics.json")
    metrics = _load("results/reconstruction/independent_gate_metrics.json")

    status = validation.get("status", "runtime status unavailable")
    condition = diagnostics.get("condition_number_on_retained_subspace")
    lines = [
        "Production runtime completed. Values below were loaded from task records and generated runtime artifacts; they are not static-preparation estimates.",
        "",
        f"- Runtime software validation: **{status}**.",
        f"- Calibration: {reduction.get('task_count')} completed tasks; {reduction.get('singles_total_raw_counts')} raw Singles and {reduction.get('hits_total_raw_counts')} raw Hits.",
        f"- System response: shape `{system.get('matrix_shape')}`, numerical rank {diagnostics.get('numerical_rank')}/{diagnostics.get('spatial_voxel_count')}, retained-subspace condition number {_fmt(condition)}.",
        f"- Pose-summed absolute sensitivity: central {_fmt(sensitivity.get('central_cps_per_bq'))} cps/Bq ({_fmt(sensitivity.get('central_cps_per_mbq'))} cps/MBq); mean {_fmt(sensitivity.get('mean_cps_per_bq'))} cps/Bq ({_fmt(sensitivity.get('mean_cps_per_mbq'))} cps/MBq); range {_fmt(sensitivity.get('minimum_cps_per_bq'))}–{_fmt(sensitivity.get('maximum_cps_per_bq'))} cps/Bq. Sequential scan-average mean: {_fmt(sensitivity.get('scan_average_mean_cps_per_bq'))} cps/Bq.",
        f"- FWHM: {fwhm.get('valid_profile_count')} valid axis profiles; mean {_fmt(fwhm.get('mean_fwhm_mm'))} mm. Invalid profiles and their crossing reasons are retained in `results/fwhm/fwhm_summary.json`.",
        f"- ASCI: **{asci.get('status')}** — {asci.get('reason')}.",
        f"- JI: {_fmt(ji.get('ji'))}; valid={ji.get('valid')}; reason={ji.get('reason')}.",
        f"- Independent GATE phantom acquisitions: {reconstruction.get('phantom_gate_tasks')} pose exposures, {reconstruction.get('gate_singles_total')} Singles total.",
        f"- Independent GATE MLEM: RMSE {_fmt(metrics.get('rmse_bq'))} Bq/voxel; normalized error {_fmt(metrics.get('normalized_error'))}; correlation {_fmt(metrics.get('correlation'))}; total-activity recovery {_fmt(metrics.get('activity_recovery_ratio'))}; hot-region contrast recovery {_fmt(metrics.get('hot_region_contrast_recovery'))}.",
        f"- Linear identifiability screen: {validation.get('scientific_reconstruction_identifiable')}; this is a rank/conditioning screen, not a resolution or image-quality guarantee.",
        "- Synthetic Poisson results are retained separately and are not treated as independent experimental validation.",
        "- Scientific acceptance requires interpretation of the measured response spectrum, independent-GATE reconstruction, residuals, and recovery metrics; software validation alone is not acceptance.",
        "",
        "### Runtime figures",
        "",
    ]
    plot_paths = list(system.get("generated_plots", [])) + list(reconstruction.get("generated_plots", []))
    if plot_paths:
        for path in plot_paths:
            relative = Path(path).relative_to(PROJECT_ROOT).as_posix() if Path(path).is_absolute() else Path(path).as_posix()
            lines.append(f"![{Path(relative).stem.replace('_', ' ')}]({relative})")
            lines.append("")
    else:
        lines.append("Runtime figure paths were not recorded.")
    return "\n".join(lines).rstrip()


def finalize() -> None:
    report = PROJECT_ROOT / "ONECUBE_IMAGING_FINAL_REPORT.md"
    text = report.read_text(encoding="utf-8")
    start = "<!-- RUNTIME_RESULTS_START -->"
    end = "<!-- RUNTIME_RESULTS_END -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError("Primary report must contain exactly one runtime-results marker pair")
    left = text.index(start) + len(start)
    right = text.index(end)
    if right <= left:
        raise RuntimeError("Runtime-results report markers are out of order")
    updated = text[:left] + "\n" + _runtime_section() + "\n" + text[right:]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=report.parent, delete=False) as stream:
        stream.write(updated)
        temporary = Path(stream.name)
    os.replace(temporary, report)
    print(f"Updated runtime results in {report}")


if __name__ == "__main__":
    try:
        finalize()
    except Exception as error:
        print(f"Report finalization failed: {error}", file=sys.stderr)
        raise SystemExit(1)
