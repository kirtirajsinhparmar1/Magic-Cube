#!/usr/bin/env python3
"""Static preparation checks for the bounded Step-5 digitizer runtime test."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNTIME_MACRO = ROOT / "magiccube_step5_digitizer_runtime_check.mac"
EXTERNAL_MACRO = ROOT / "magiccube_step5_hits_external.mac"
JOB = ROOT / "magiccube_step5_digitizer_runtime_job.sh"

FROZEN_HASHES = {
    "magiccube_production_geometry.mac": "3adf6843a7198889a4bc6ce07809fcf071af62111e1dfbb1e3535c29e8a880be",
    "magiccube_production_system.mac": "319019484bf798b7f294cc3ccb756d3e5c8c98b8cc013289b2e83a8c21e3fb76",
    "magiccube_production_physics.mac": "c56fc7e98a906d7a89e538e794456cf81f174d75078256dc55beaf72118a5df3",
    "magiccube_production_digitizer.mac": "a8d96bc08ec38857667f0ec6621cb1d7b2c0651f15aa77619be71731579cd9b4",
    "detector_map.csv": "dd7ca66a2b06bf091d229693bca48091d762a2d5c4508e12668ccfcaf363849c",
}

FAMILIES = ("mc_gagg_ee", "mc_gagg_eo", "mc_gagg_oe", "mc_gagg_oo")


def active_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_runtime_signature(lines: list[str]) -> list[str]:
    prefixes = ("/gate/source/", "/gate/random/", "/gate/application/")
    return [line for line in lines if line.startswith(prefixes)]


def find_index(lines: list[str], command: str) -> int:
    try:
        return lines.index(command)
    except ValueError:
        return -1


def error(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    if not RUNTIME_MACRO.is_file():
        error(errors, "runtime digitizer macro is missing")
    if not EXTERNAL_MACRO.is_file():
        error(errors, "validated external Hits macro is missing")
    if not JOB.is_file():
        error(errors, "runtime job is missing")
    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        print("STATIC DIGITIZER-RUNTIME PREPARATION: BLOCKED")
        return 1

    runtime = active_lines(RUNTIME_MACRO)
    external = active_lines(EXTERNAL_MACRO)
    job_text = JOB.read_text(encoding="utf-8")

    for filename, expected_hash in FROZEN_HASHES.items():
        path = ROOT / filename
        actual_hash = sha256(path) if path.is_file() else "MISSING"
        if actual_hash != expected_hash:
            error(errors, f"frozen file changed or missing: {filename}")
        else:
            print(f"- {filename} unchanged")

    required_executes = (
        "/control/execute magiccube_production_geometry.mac",
        "/control/execute magiccube_production_system.mac",
        "/control/execute magiccube_production_physics.mac",
        "/control/execute magiccube_production_digitizer.mac",
    )
    for command in required_executes:
        if command not in runtime:
            error(errors, f"missing required execution command: {command}")

    initialize_index = find_index(runtime, "/gate/run/initialize")
    digitizer_index = find_index(
        runtime, "/control/execute magiccube_production_digitizer.mac"
    )
    source_index = find_index(runtime, "/gate/source/addSource external_140kev_smoke gps")
    if not (initialize_index >= 0 and digitizer_index > initialize_index and source_index > digitizer_index):
        error(errors, "macro order is not initialize -> digitizer -> source")
    else:
        print("- macro order is geometry/system/physics -> initialize -> digitizer -> source")

    if find_index(external, "/gate/run/initialize") < 0:
        error(errors, "validated external macro has no initialization command")
    else:
        external_init = find_index(external, "/gate/run/initialize")
        runtime_init = find_index(runtime, "/gate/run/initialize")
        if runtime[: runtime_init + 1] != external[: external_init + 1]:
            error(errors, "pre-initialization setup differs from validated external macro")
        else:
            print("- pre-initialization setup matches validated external macro")

    if source_runtime_signature(runtime) != source_runtime_signature(external):
        error(errors, "source/RNG/acquisition commands differ from validated external macro")
    else:
        print("- source/RNG/acquisition commands match validated external macro")

    if "/gate/output/tree/enable" not in runtime:
        error(errors, "tree output is not enabled")
    if "/gate/output/tree/hits/enable" not in runtime:
        error(errors, "Hits output is not enabled")
    singles_requests = [line for line in runtime if line == "/gate/output/tree/addCollection Singles"]
    if len(singles_requests) != 1:
        error(errors, "the shared Singles collection is not requested exactly once")
    else:
        print("- Hits enabled and shared Singles output requested for four digitizer managers")

    expected_output = (
        "/gate/output/tree/addFileName "
        "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_digitizer/"
        "magiccube_step5_digitizer.root"
    )
    if expected_output not in runtime:
        error(errors, "new digitizer output prefix is missing or incorrect")

    if any(line.startswith("/gate/digitizerMgr/") for line in runtime):
        error(errors, "digitizer commands were duplicated instead of executing the frozen macro")
    if runtime.count("/control/execute magiccube_production_digitizer.mac") != 1:
        error(errors, "production digitizer must be executed exactly once")

    for family in FAMILIES:
        if family not in (ROOT / "magiccube_production_digitizer.mac").read_text(
            encoding="utf-8"
        ):
            error(errors, f"frozen digitizer family missing: {family}")

    required_job_strings = (
        'WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"',
        'OUTPUT_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_digitizer"',
        'PYTHON="/user/kmparmar/venv/bin/python"',
        "module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2",
        "module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2",
        "#SBATCH --output=magiccube_step5_digitizer_%j.out",
        "#SBATCH --error=magiccube_step5_digitizer_%j.err",
        "magiccube_step5_digitizer_runtime_check.mac",
        "validate_magiccube_step5_digitizer_runtime_outputs.py",
    )
    for required in required_job_strings:
        if required not in job_text:
            error(errors, f"job missing required text: {required}")
    if re.search(r"dirname\s+['\"]?\$0", job_text):
        error(errors, "job contains the forbidden dirname-$0 spool-path pattern")
    gate_lines = [line for line in job_text.splitlines() if re.match(r"^Gate\s+", line)]
    if len(gate_lines) != 1:
        error(errors, "job must contain exactly one Gate invocation")
    else:
        print("- one bounded Gate invocation uses explicit WORKDIR")

    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        print("STATIC DIGITIZER-RUNTIME PREPARATION: BLOCKED")
        return 1

    print("- validated external source is reused without scientific changes")
    print("- frozen production digitizer remains the only digitizer implementation")
    print("STATIC DIGITIZER-RUNTIME PREPARATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
