"""Reference-method JI calculation."""

from __future__ import annotations

from typing import Any

import numpy as np


def calculate_ji(
    mean_sensitivity_cps_per_bq: float,
    fwhm_mm: list[float] | np.ndarray,
    asci_percent: float,
) -> dict[str, Any]:
    """Use JI=(mean sensitivity / mean FWHM^2) * (ASCI percent / 100)."""
    valid_widths = np.asarray(fwhm_mm, dtype=float)
    valid_widths = valid_widths[np.isfinite(valid_widths) & (valid_widths > 0)]
    mean_fwhm = float(valid_widths.mean()) if valid_widths.size else None
    result: dict[str, Any] = {
        "formula": "(mean_sensitivity_cps_per_bq / mean_fwhm_mm^2) * (mean_asci_percent / 100)",
        "mean_sensitivity_cps_per_bq": float(mean_sensitivity_cps_per_bq),
        "mean_fwhm_mm": mean_fwhm,
        "mean_asci_percent": float(asci_percent),
        "ji": None,
        "valid": False,
        "reason": None,
    }
    if mean_fwhm is None:
        result["reason"] = "no valid FWHM profiles; JI is not scientifically computable"
        return result
    result["ji"] = float((mean_sensitivity_cps_per_bq / (mean_fwhm**2)) * (asci_percent / 100.0))
    result["valid"] = True
    return result
