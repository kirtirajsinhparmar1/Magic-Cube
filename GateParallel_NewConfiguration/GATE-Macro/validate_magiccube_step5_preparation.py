#!/usr/bin/env python3
"""Static preparation checks for the faithful Magic-Cube Step-5 port.

This validator never invokes GATE, Slurm, ROOT, or any production pipeline.
The frozen-file hashes were captured immediately before the Step-5 files were
created in this audit.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GAGG_FAMILIES = (
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
)

# These are the frozen Step-1--Step-4 artifacts that this task is not allowed
# to modify.  A hash mismatch is a hard failure, not a warning.
FROZEN_SHA256 = {
    "magiccube_geometry.mac": "b2f6224e0cf129202edfc8e50c2677d967039689fbbfef4958208f0e5268001e",
    "detector_map.csv": "dd7ca66a2b06bf091d229693bca48091d762a2d5c4508e12668ccfcaf363849c",
    "magiccube_lattice_map.csv": "a81702367aaa786fb08f4e4839e5c2f9834881f4b39d4574a53e0c6986902533",
    "magiccube_runtime_system.mac": "283e8cd6da288d8e1e36cf13e3a8b6767cc4b939017aa0a82a52e64a8925516c",
    "magiccube_runtime_physics.mac": "c7e1df4c6ac693649ef62a8350d473ddda92666ca8a027fbb8624c1a441b28ce",
    "magiccube_runtime_identity.json": "a4432b31948e07b189efa041654f93dbe2affa271d2d1d7104e5bbba8f04d62d",
}


def active_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    failures: list[str] = []

    def check(condition: bool, label: str, detail: str = "") -> None:
        if condition:
            print(f"PASS: {label}")
        else:
            message = f"FAIL: {label}"
            if detail:
                message += f" — {detail}"
            print(message)
            failures.append(message)

    physics_path = ROOT / "magiccube_production_physics.mac"
    digitizer_path = ROOT / "magiccube_production_digitizer.mac"
    harness_path = ROOT / "magiccube_step5_digitizer_check.mac"
    job_path = ROOT / "magiccube_step5_digitizer_job.sh"

    check(physics_path.is_file(), "production physics macro exists")
    check(digitizer_path.is_file(), "production digitizer macro exists")
    check(harness_path.is_file(), "bounded digitizer harness exists")
    check(job_path.is_file(), "manual Slurm harness exists")

    physics_lines = active_lines(physics_path)
    physics_text = file_text(physics_path)
    check(
        physics_lines.count("/gate/physics/addProcess PhotoElectric") == 1,
        "PhotoElectric is active exactly once",
    )
    check(
        physics_lines.count(
            "/gate/physics/processes/PhotoElectric/setModel StandardModel"
        )
        == 1,
        "PhotoElectric uses StandardModel",
    )
    disabled_process_names = (
        "Compton",
        "RayleighScattering",
        "ElectronIonisation",
        "Bremsstrahlung",
        "PositronAnnihilation",
        "MultipleScattering",
    )
    active_disabled = [
        line
        for line in physics_lines
        if any(name.lower() in line.lower() for name in disabled_process_names)
    ]
    check(
        not active_disabled,
        "original disabled physics processes remain inactive",
        "; ".join(active_disabled),
    )
    try:
        process_enabled = physics_lines.index("/gate/physics/processList Enabled")
        process_initialized = physics_lines.index(
            "/gate/physics/processList Initialized"
        )
        process_order_ok = process_enabled < process_initialized
    except ValueError:
        process_order_ok = False
    check(
        process_order_ok,
        "physics process-list order is Enabled then Initialized",
    )
    expected_cut_lines = {
        f"/gate/physics/{particle}/SetCutInRegion {family} 1.0 cm"
        for family in GAGG_FAMILIES
        for particle in ("Gamma", "Electron", "Positron")
    }
    actual_cut_lines = {
        line
        for line in physics_lines
        if "/SetCutInRegion " in line
    }
    check(
        actual_cut_lines == expected_cut_lines,
        "all four GAGG families have the original 1.0 cm cuts",
        f"missing={sorted(expected_cut_lines - actual_cut_lines)} "
        f"unexpected={sorted(actual_cut_lines - expected_cut_lines)}",
    )
    check(
        not any("xlayer" in line.lower() for line in physics_lines),
        "production physics has no legacy xlayer targets",
    )
    check(
        not any("k9" in line.lower() for line in physics_lines),
        "production physics has no K9 target",
    )
    check(
        "#/gate/physics/addProcess Compton" in physics_text,
        "disabled-process trace is retained as comments",
    )

    digitizer_lines = active_lines(digitizer_path)
    manager_pattern = re.compile(
        r"^/gate/digitizerMgr/([^/\s]+)/SinglesDigitizer/Singles/(.+)$"
    )
    managers: set[str] = set()
    per_family: dict[str, list[str]] = {family: [] for family in GAGG_FAMILIES}
    unmatched_digitizer_lines: list[str] = []
    for line in digitizer_lines:
        match = manager_pattern.match(line)
        if not match:
            unmatched_digitizer_lines.append(line)
            continue
        manager, command = match.groups()
        managers.add(manager)
        if manager in per_family:
            per_family[manager].append(command)
    check(
        managers == set(GAGG_FAMILIES),
        "digitizer targets exactly the four GAGG families",
        f"targets={sorted(managers)}",
    )
    check(
        not unmatched_digitizer_lines,
        "all active digitizer commands use the expected Singles path",
        "; ".join(unmatched_digitizer_lines),
    )
    expected_module_order = [
        "insert adder",
        "insert energyResolution",
        "insert spatialResolution",
        "insert energyFraming",
    ]
    for family in GAGG_FAMILIES:
        commands = per_family[family]
        module_order = [command for command in commands if command.startswith("insert ")]
        expected_parameters = {
            "insert adder",
            "insert energyResolution",
            "energyResolution/fwhm 0.10",
            "energyResolution/energyOfReference 140. keV",
            "insert spatialResolution",
            "spatialResolution/fwhm 1.0 mm",
            "spatialResolution/confineInsideOfSmallestElement true",
            "spatialResolution/verbose 0",
            "insert energyFraming",
            "energyFraming/setMin 120. keV",
            "energyFraming/setMax 160. keV",
        }
        check(
            module_order == expected_module_order,
            f"{family} module order is adder, energyResolution, spatialResolution, energyFraming",
            f"order={module_order}",
        )
        check(
            set(commands) == expected_parameters and len(commands) == 11,
            f"{family} preserves every original digitizer parameter",
            f"commands={commands}",
        )
    check(
        len(digitizer_lines) == 44,
        "digitizer contains only the four 11-command original-style chains",
        f"active command count={len(digitizer_lines)}",
    )
    forbidden_digitizer_terms = re.compile(
        r"dead\s*time|pile\s*up|efficiency|coincidence", re.IGNORECASE
    )
    active_forbidden_digitizer = [
        line for line in digitizer_lines if forbidden_digitizer_terms.search(line)
    ]
    check(
        not active_forbidden_digitizer,
        "no deadtime, pile-up, efficiency, or coincidence module is active",
        "; ".join(active_forbidden_digitizer),
    )
    check(
        not any("xlayer" in line.lower() or "k9" in line.lower() for line in digitizer_lines),
        "production digitizer has no legacy or passive-material targets",
    )

    system_path = ROOT / "magiccube_runtime_system.mac"
    system_lines = active_lines(system_path)
    expected_system_lines = [
        f"/gate/{family}/attachCrystalSDnoSystem" for family in GAGG_FAMILIES
    ]
    check(
        system_lines == expected_system_lines,
        "frozen runtime system still attaches no-system SD to four GAGG families",
        f"active commands={system_lines}",
    )
    check(
        not any(re.search(r"/attachCrystalSD\s*$", line) for line in system_lines),
        "frozen runtime system has no system-dependent attachCrystalSD command",
    )
    check(
        not any("k9" in line.lower() for line in system_lines),
        "frozen runtime system leaves K9 passive",
    )

    for relative, expected in FROZEN_SHA256.items():
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else "MISSING"
        check(actual == expected, f"frozen file unchanged: {relative}", f"sha256={actual}")

    identity_path = ROOT / "magiccube_runtime_identity.json"
    identity_text = file_text(identity_path)
    check(
        "POSITION_DERIVED_REQUIRED" in identity_text,
        "runtime identity policy remains POSITION_DERIVED_REQUIRED",
    )
    try:
        with (ROOT / "detector_map.csv").open(newline="", encoding="utf-8") as stream:
            detector_rows = list(csv.DictReader(stream))
        detector_ids = [int(row["detector_id"]) for row in detector_rows]
        detector_map_ok = len(detector_rows) == 2048 and detector_ids == list(range(2048))
    except (OSError, KeyError, ValueError):
        detector_map_ok = False
        detector_rows = []
    check(
        detector_map_ok,
        "detector_map.csv still defines canonical detector IDs 0..2047",
        f"rows={len(detector_rows)}",
    )

    harness_text = file_text(harness_path)
    harness_requirements = (
        "/control/execute magiccube_geometry.mac",
        "/control/execute magiccube_runtime_system.mac",
        "/control/execute magiccube_production_physics.mac",
        "/control/execute magiccube_production_digitizer.mac",
        "/gate/source/step5_smoke/gps/ene/mono 140.0 keV",
        "/gate/source/step5_smoke/gps/pos/centre 0.0 0.0 -66.0 mm",
        "/gate/output/tree/hits/enable",
        "/gate/output/tree/addCollection Singles",
        "/gate/application/startDAQ",
    )
    check(
        all(requirement in harness_text for requirement in harness_requirements),
        "bounded harness uses frozen geometry, original-style physics/digitizer, smoke source, Hits, and Singles",
    )
    job_text = file_text(job_path)
    check(
        "#SBATCH --cluster=ub-hpc" in job_text
        and "#SBATCH --partition=general-compute" in job_text
        and "#SBATCH --qos=general-compute" in job_text,
        "manual harness records the UB CCR scheduler convention",
    )
    check(
        "Gate magiccube_step5_digitizer_check.mac" in job_text
        and "validate_magiccube_step5_outputs.py" in job_text,
        "manual harness invokes Gate only when the user runs the job and then validates outputs",
    )

    if failures:
        print(f"STATIC PREPARATION: FAIL ({len(failures)} failed checks)")
        return 1
    print("STATIC PREPARATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
