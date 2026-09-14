#!/usr/bin/env python3
"""Validate real Magic-Cube Step-4 outputs without inventing runtime evidence."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


WORKDIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(
    "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step4"
)
IDENTITY_JSON = WORKDIR / "magiccube_runtime_identity.json"
COMPLETE_IDENTITIES = {
    "ID_ONLY_VALIDATED",
    "ID_PLUS_FAMILY_VALIDATED",
    "POSITION_DERIVED_REQUIRED",
}
ALL_IDENTITIES = COMPLETE_IDENTITIES | {"UNRESOLVED"}
EXPECTED_FAMILIES = {
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
}


def close_values(actual: Any, expected: list[float]) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    try:
        return all(
            math.isclose(float(value), target, rel_tol=0.0, abs_tol=1.0e-9)
            for value, target in zip(actual, expected)
        )
    except (TypeError, ValueError):
        return False


def read_status(path: Path, failures: list[str]) -> dict[str, Any] | None:
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"unreadable runtime status {path.name}: {exc}")
        return None
    if status.get("exit_code") != 0:
        failures.append(f"{path.name} does not record Gate exit code 0")
    root_files = status.get("root_files")
    if not isinstance(root_files, list) or not root_files:
        failures.append(f"{path.name} records no current ROOT output")
    return status


def main() -> int:
    geometry_status = OUTPUT_DIR / "geometry_check.exit_code"
    runtime_statuses = list(OUTPUT_DIR.glob("*.status.json")) if OUTPUT_DIR.is_dir() else []
    if not IDENTITY_JSON.is_file():
        if not geometry_status.is_file() and not runtime_statuses:
            print("Magic-Cube Step-4 runtime validation: NOT_RUN")
            return 2
        print("Magic-Cube Step-4 runtime validation: FAIL")
        print(f"- missing runtime identity report: {IDENTITY_JSON}")
        return 1

    try:
        report = json.loads(IDENTITY_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("Magic-Cube Step-4 runtime validation: FAIL")
        print(f"- unreadable runtime identity report: {exc}")
        return 1

    failures: list[str] = []
    geometry = report.get("geometry_initialization", {})
    probes = report.get("probe_summary", {})
    schema = report.get("root_schema_discovery", {})
    sensitive = report.get("sensitive_detector", {})
    identity = report.get("identity", {})
    smoke = report.get("smoke_140kev", {})

    probe_status_paths = sorted(OUTPUT_DIR.glob("probe_[0-9][0-9].status.json"))
    smoke_status_paths = sorted(OUTPUT_DIR.glob("smoke_140kev.status.json"))
    if len(probe_status_paths) != 32:
        failures.append("exactly 32 current probe status files are required")
    if len(smoke_status_paths) != 1:
        failures.append("exactly one current smoke status file is required")
    for status_path in probe_status_paths + smoke_status_paths:
        read_status(status_path, failures)

    if report.get("status") != "COMPLETE":
        failures.append("runtime inspector did not reach COMPLETE")
    if not geometry.get("executed") or not geometry.get("passed"):
        failures.append("geometry-only Gate initialization did not pass")
    if probes.get("status_records") != 32:
        failures.append("exactly 32 probe status records are required")
    if probes.get("root_files_analyzed") != 32:
        failures.append("exactly 32 current probe ROOT files must be analyzed")
    if probes.get("analyzed_probes") != 32:
        failures.append("all 32 fixed probes must be analyzable")
    if probes.get("successful_probes") != 32:
        failures.append("all 32 fixed probes must have useful expected-GAGG hits")
    if int(probes.get("total_hits", 0)) <= 0:
        failures.append("probe ROOT files contain no positive-energy-deposition hits")
    if int(probes.get("invalid_detector_ids", -1)) != 0:
        failures.append("mapped canonical detector IDs must remain in 0...2047")
    if int(probes.get("unmapped_hits", -1)) != 0:
        failures.append("probe data contain unmapped hit positions")
    if int(probes.get("ambiguous_hits", -1)) != 0:
        failures.append("probe data contain ambiguously mapped hit positions")

    family_results = probes.get("families_with_useful_hits", {})
    if set(family_results) != EXPECTED_FAMILIES or not all(family_results.values()):
        failures.append("all four and only the four GAGG families need useful hits")
    if not schema.get("required_fields_available"):
        failures.append("ROOT schema lacks eventID/edep/position fields")

    classification = identity.get("classification")
    if classification not in ALL_IDENTITIES:
        failures.append("runtime identity classification is invalid or missing")
    elif classification == "UNRESOLVED":
        failures.append("runtime detector identity remains UNRESOLVED")
    elif classification not in COMPLETE_IDENTITIES:
        failures.append("runtime detector identity is incomplete")
    if (
        classification == "POSITION_DERIVED_REQUIRED"
        and not identity.get("position_mapping_validated")
    ):
        failures.append("position-derived identity was not uniquely validated")

    if sensitive.get("k9_sensitive") is not False:
        failures.append("K9 did not remain passive")
    if int(sensitive.get("k9_sensitive_hits", -1)) != 0:
        failures.append("runtime evidence contains K9-sensitive hits")

    if smoke.get("status_records") != 1:
        failures.append("exactly one external 140-keV smoke run is required")
    if int(smoke.get("root_files_analyzed", 0)) < 1 or not smoke.get("executed"):
        failures.append("external 140-keV smoke run did not produce analyzable ROOT output")
    if int(smoke.get("total_hits", 0)) <= 0:
        failures.append("external 140-keV smoke run recorded no GAGG hits")
    if int(smoke.get("k9_sensitive_hits", -1)) != 0:
        failures.append("external smoke output contains K9-sensitive hits")
    source = smoke.get("source")
    if not isinstance(source, dict):
        failures.append("external smoke source metadata are missing")
    else:
        try:
            energy_kev = float(source.get("energy_kev"))
        except (TypeError, ValueError):
            energy_kev = math.nan
        if not math.isclose(energy_kev, 140.0, rel_tol=0.0, abs_tol=1.0e-9):
            failures.append("external smoke energy is not 140 keV")
        if not close_values(source.get("position_mm"), [0.0, 0.0, -66.0]):
            failures.append("external smoke position is not (0,0,-66) mm")

    if failures:
        print("Magic-Cube Step-4 runtime validation: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Magic-Cube Step-4 runtime validation: PASS")
    print(f"Runtime detector identity: {classification}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
