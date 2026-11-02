from __future__ import annotations

from typing import Any


def calculate_ji(
    sensitivity_summary: dict[str, Any],
    fwhm_summary: dict[str, Any],
    asci_result: dict[str, Any],
) -> dict[str, Any]:
    sensitivity = sensitivity_summary.get("mean_cps_per_bq")
    fwhm = fwhm_summary.get("mean_fwhm_mm")
    asci_percent = asci_result.get("mean_percent") if asci_result.get("defined") else None
    if sensitivity is None or sensitivity <= 0:
        reason = "mean sensitivity is unavailable or non-positive"
    elif fwhm is None or fwhm <= 0:
        reason = "no valid half-maximum FWHM profiles"
    elif asci_percent is None:
        reason = "ASCI is not physically applicable to the bare uncollimated OneCube detector"
    else:
        return {
            "formula": "(mean_sensitivity_cps_per_bq / mean_fwhm_mm^2) * (asci_percent / 100)",
            "mean_sensitivity_cps_per_bq": sensitivity,
            "mean_fwhm_mm": fwhm,
            "mean_asci_percent": asci_percent,
            "ji": float((sensitivity / (fwhm ** 2)) * (asci_percent / 100.0)),
            "valid": True,
            "reason": None,
        }
    return {
        "formula": "(mean_sensitivity_cps_per_bq / mean_fwhm_mm^2) * (asci_percent / 100)",
        "mean_sensitivity_cps_per_bq": sensitivity,
        "mean_fwhm_mm": fwhm,
        "mean_asci_percent": asci_percent,
        "ji": None,
        "valid": False,
        "reason": reason,
    }

