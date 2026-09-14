#!/usr/bin/env python3
"""Purely static readiness checks for the manual Magic-Cube Step-4 job."""

from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path
from typing import Any


WORKDIR = Path(__file__).resolve().parent
EXPECTED_WORKDIR = (
    "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/"
    "mcsim/GateParallel_NewConfiguration/GATE-Macro"
)
EXPECTED_OUTPUT_DIR = (
    "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step4"
)
EXPECTED_FAMILIES = (
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
)
EXPECTED_GEOMETRY_FAMILIES = (
    "mc_gagg_ee",
    "mc_k9_ee",
    "mc_gagg_eo",
    "mc_k9_eo",
    "mc_gagg_oe",
    "mc_k9_oe",
    "mc_gagg_oo",
    "mc_k9_oo",
)
EXPECTED_PROBES = (
    (0, 0, 0),
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (7, 0, 0),
    (0, 7, 0),
    (0, 0, 7),
    (7, 7, 7),
)
REQUIRED_FILES = (
    "MAGIC_CUBE_V1_SPEC.md",
    "MAGIC_CUBE_V1_MATERIALS.md",
    "MAGIC_CUBE_V1_GEOMETRY.md",
    "magiccube_v1_config.json",
    "GateMaterials.db",
    "generate_magiccube_geometry.py",
    "magiccube_geometry.mac",
    "magiccube_lattice_map.csv",
    "detector_map.csv",
    "validate_magiccube_geometry.py",
    "magiccube_runtime_geometry_check.mac",
    "magiccube_runtime_system.mac",
    "magiccube_runtime_physics.mac",
    "run_magiccube_step4_runtime.py",
    "magiccube_step4_job.sh",
    "inspect_magiccube_runtime.py",
    "validate_magiccube_runtime.py",
    "MAGIC_CUBE_V1_RUNTIME_VALIDATION.md",
    "validate_magiccube_step4_preparation.py",
    "MAGIC_CUBE_STEP4_MANUAL_RUNBOOK.md",
)


class Checks:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.failures.append(message)


def read_text(name: str) -> str:
    return (WORKDIR / name).read_text(encoding="utf-8")


def csv_rows(name: str) -> list[dict[str, str]]:
    with (WORKDIR / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def literal_assignments(source: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
        value = node.value
        if isinstance(target, ast.Name) and value is not None:
            try:
                values[target.id] = ast.literal_eval(value)
            except (ValueError, TypeError):
                pass
    return values


def command_text(source: str) -> str:
    return "\n".join(
        line.strip() for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")
    )


def check_required_files(checks: Checks) -> None:
    for name in REQUIRED_FILES:
        checks.require((WORKDIR / name).is_file(), f"required file is missing: {name}")


def check_frozen_maps(checks: Checks) -> None:
    lattice = csv_rows("magiccube_lattice_map.csv")
    detectors = csv_rows("detector_map.csv")
    checks.require(len(lattice) == 4096, "lattice map must contain exactly 4096 data rows")
    checks.require(len(detectors) == 2048, "detector map must contain exactly 2048 data rows")
    try:
        detector_ids = [int(row["detector_id"]) for row in detectors]
    except (KeyError, ValueError):
        checks.require(False, "detector map has an invalid detector_id column")
        return
    checks.require(
        len(set(detector_ids)) == 2048 and set(detector_ids) == set(range(2048)),
        "detector IDs must be unique and span exactly 0...2047",
    )


def sbatch_options(job: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for line in job.splitlines():
        match = re.match(r"^#SBATCH\s+--([^=\s]+)(?:=(\S+))?\s*$", line)
        if match:
            options[match.group(1)] = match.group(2) or ""
    return options


def check_job(checks: Checks) -> None:
    job = read_text("magiccube_step4_job.sh")
    options = sbatch_options(job)
    checks.require(job.startswith("#!/bin/bash\n"), "job script shebang must be #!/bin/bash")
    checks.require("set -euo pipefail" in job, "job script must use set -euo pipefail")
    expected_options = {
        "cluster": "ub-hpc",
        "partition": "general-compute",
        "qos": "general-compute",
        "nodes": "1",
        "ntasks": "1",
        "cpus-per-task": "1",
        "mem": "4G",
        "time": "00:20:00",
        "output": "magiccube_step4_%j.out",
        "error": "magiccube_step4_%j.err",
    }
    for option, expected in expected_options.items():
        checks.require(
            options.get(option) == expected,
            f"job option --{option} must equal {expected}",
        )
    checks.require("array" not in options, "Step-4 job must not be an array job")
    checks.require(f'WORKDIR="{EXPECTED_WORKDIR}"' in job, "job has the wrong working directory")
    checks.require(f'RUNTIME_DIR="{EXPECTED_OUTPUT_DIR}"' in job, "job has the wrong runtime directory")
    checks.require('cd "$WORKDIR"' in job, "job must change directory using the quoted WORKDIR")
    checks.require('mkdir -p "$RUNTIME_DIR"' in job, "job must create the quoted runtime directory")
    checks.require("Tridev" not in job and "/user/tridevme" not in job, "job contains a stale Tridev path")

    executable = command_text(job)
    nested = re.findall(r"(?m)^\s*(?:sbatch|srun|salloc)\b", executable)
    checks.require(not nested, "job contains a nested Slurm launch command")
    module_tokens = (
        "gcc/11.2.0",
        "geant4/11.2.1",
        "geant4-data/11.2",
        "openmpi/4.1.1",
        "gate/9.4",
    )
    for token in module_tokens:
        checks.require(token in job, f"job module setup is missing {token}")
    for token in ("hostname", "date --iso-8601=seconds", "pwd", "module list", "which Gate", "Gate --version", "geant4-config --version"):
        checks.require(token in job, f"environment capture is missing: {token}")
    checks.require(
        'env -u PYTHONPATH "$PYTHON"' in job,
        "job does not isolate the analysis Python from module PYTHONPATH",
    )

    workflow = (
        "validate_magiccube_geometry.py",
        "Gate magiccube_runtime_geometry_check.mac",
        "run_magiccube_step4_runtime.py",
        "inspect_magiccube_runtime.py",
        "validate_magiccube_runtime.py",
    )
    positions = [job.find(token) for token in workflow]
    checks.require(all(position >= 0 for position in positions), "job is missing a Step-4 workflow stage")
    checks.require(positions == sorted(positions), "job workflow stages are not in the required order")


def check_runtime_macros(checks: Checks) -> None:
    geometry = read_text("magiccube_runtime_geometry_check.mac")
    detector_geometry = read_text("magiccube_geometry.mac")
    system = read_text("magiccube_runtime_system.mac")
    physics = read_text("magiccube_runtime_physics.mac")
    geometry_commands = command_text(geometry)
    detector_geometry_commands = command_text(detector_geometry)
    system_commands = command_text(system)
    physics_commands = command_text(physics)

    checks.require("GateMaterials.db" in geometry_commands, "geometry check does not select GateMaterials.db")
    checks.require("magiccube_geometry.mac" in geometry_commands, "geometry check does not execute Magic-Cube geometry")
    checks.require("/gate/run/initialize" in geometry_commands, "geometry check does not initialize Gate")
    for axis in ("X", "Y", "Z"):
        checks.require(
            f"/gate/world/geometry/set{axis}Length 200.0 mm" in geometry_commands,
            f"geometry-check world {axis} length is not 200 mm",
        )
    checks.require("/gate/application/startDAQ" not in geometry_commands, "geometry-only macro must not run events")

    no_autocenter_families = tuple(re.findall(
        r"(?m)^/gate/([^/\s]+)/cubicArray/autoCenter\s+false\s*$",
        detector_geometry_commands,
    ))
    all_autocenter_settings = re.findall(
        r"(?m)^/gate/([^/\s]+)/cubicArray/autoCenter\s+(\S+)\s*$",
        detector_geometry_commands,
    )
    checks.require(
        no_autocenter_families == EXPECTED_GEOMETRY_FAMILIES,
        "geometry macro must disable cubicArray autoCenter for exactly all eight families",
    )
    checks.require(
        len(all_autocenter_settings) == 8
        and all(value.lower() == "false" for _, value in all_autocenter_settings),
        "geometry macro must contain exactly eight explicit false autoCenter settings",
    )
    for family in EXPECTED_GEOMETRY_FAMILIES:
        checks.require(
            detector_geometry_commands.count(
                f"/gate/{family}/repeaters/insert cubicArray"
            ) == 1,
            f"geometry macro must define one cubicArray for {family}",
        )

    attachments = re.findall(
        r"(?m)^/gate/([^/\s]+)/attachCrystalSDnoSystem\s*$", system_commands
    )
    plain_attachments = re.findall(
        r"(?m)^/gate/([^/\s]+)/attachCrystalSD\s*$", system_commands
    )
    checks.require(
        tuple(attachments) == EXPECTED_FAMILIES,
        "sensitive macro must use attachCrystalSDnoSystem for exactly the four GAGG families",
    )
    checks.require(
        not plain_attachments,
        "Magic-Cube GAGG families must not use system-dependent attachCrystalSD",
    )
    checks.require(not any("k9" in name.lower() for name in attachments), "a K9 family is attached as sensitive")
    checks.require("PhotoElectric" in physics_commands, "diagnostic physics must include PhotoElectric")
    for final_process in ("Compton", "Rayleigh", "Optical"):
        checks.require(final_process not in physics_commands, f"diagnostic physics unexpectedly includes {final_process}")

    combined = "\n".join(
        (geometry_commands, detector_geometry_commands, system_commands, physics_commands)
    ).lower()
    for forbidden in (
        "xlayer",
        "tungsten",
        "metalplate",
        "plate.mac",
        "cylindricalpet",
    ):
        checks.require(forbidden not in combined, f"runtime macros contain forbidden legacy token: {forbidden}")


def check_probe_and_source_design(checks: Checks) -> None:
    runner = read_text("run_magiccube_step4_runtime.py")
    values = literal_assignments(runner)
    families = tuple(values.get("GAGG_FAMILIES", ()))
    probes = tuple(tuple(item) for item in values.get("PROBE_COORDINATES", ()))
    checks.require(families == EXPECTED_FAMILIES, "runner must define exactly four GAGG families")
    checks.require(probes == EXPECTED_PROBES, "runner fixed probe coordinates do not match the contract")
    checks.require(len(families) * len(probes) == 32, "runner must intend exactly 32 probes")
    checks.require("detector_map.csv" in runner, "runner does not use detector_map.csv")
    for field in ("detector_id", "ix", "iy", "d", "physical_layer_k", "x_mm", "y_mm", "z_mm"):
        checks.require(field in runner, f"runner does not obtain required detector-map field: {field}")
    checks.require(EXPECTED_OUTPUT_DIR in runner, "runner does not use the dedicated Step-4 output directory")
    checks.require(
        "/gate/output/tree/hits/enable" in runner,
        "runner does not enable raw Tree hit output",
    )
    checks.require(
        "/gate/output/tree/singles/disable" not in runner,
        "runner contains the invalid GATE 9.4 Tree Singles-disable command",
    )

    checks.require(
        math_close(values.get("PROBE_ENERGY_KEV"), 30.0),
        "diagnostic probe energy must be approximately 30 keV",
    )
    checks.require(
        math_close(values.get("SMOKE_ENERGY_KEV"), 140.0),
        "external smoke energy must be 140 keV",
    )
    checks.require(
        tuple(values.get("SMOKE_SOURCE_MM", ())) == (0.0, 0.0, -66.0),
        "external smoke position must be (0,0,-66) mm",
    )
    probe_events = float(values.get("PROBE_ACTIVITY_BQ", 0.0)) * float(values.get("RUN_DURATION_S", 0.0))
    smoke_events = float(values.get("SMOKE_ACTIVITY_BQ", 0.0)) * float(values.get("RUN_DURATION_S", 0.0))
    checks.require(50.0 <= probe_events <= 100.0, "probe event scale must remain between 50 and 100 primaries")
    checks.require(10_000.0 <= smoke_events <= 50_000.0, "smoke event scale must remain between 10,000 and 50,000 primaries")
    checks.require(smoke_events <= 100_000.0, "smoke event scale exceeds the hard 100,000-primary limit")


def math_close(value: Any, target: float) -> bool:
    try:
        return abs(float(value) - target) <= 1.0e-9
    except (TypeError, ValueError):
        return False


def check_inspector_and_runtime_validator(checks: Checks) -> None:
    inspector = read_text("inspect_magiccube_runtime.py")
    runtime_validator = read_text("validate_magiccube_runtime.py")
    for token in ("import uproot", "discover_hit_tree", "root_keys", "selected_tree"):
        checks.require(token in inspector, f"ROOT inspector lacks schema-discovery logic: {token}")
    for token in ("containing_rows", "POSITION_TOLERANCE_MM", "detector_map.csv"):
        checks.require(token in inspector, f"ROOT inspector lacks position mapping logic: {token}")
    checks.require(
        'status.get("exit_code") != 0' in inspector,
        "ROOT inspector does not reject nonzero Gate status before opening ROOT files",
    )
    checks.require(
        "expected_probe_root_file" in inspector,
        "ROOT inspector does not select the expected GAGG hit collection",
    )
    checks.require(
        'status.get("exit_code") != 0' in runtime_validator,
        "runtime validator does not independently require Gate exit code 0",
    )
    checks.require("0 <= int(row[\"mapped_detector_id\"]) <= 2047" in inspector, "ROOT inspector lacks detector-ID range checking")
    for identity_class in (
        "ID_ONLY_VALIDATED",
        "ID_PLUS_FAMILY_VALIDATED",
        "POSITION_DERIVED_REQUIRED",
        "UNRESOLVED",
    ):
        checks.require(identity_class in inspector, f"ROOT inspector lacks identity class: {identity_class}")
    checks.require("permutations((\"rx\", \"ry\", \"rz\"))" in inspector, "ROOT inspector does not limit flattening tests to axis permutations")
    checks.require("volumeID[6]" not in inspector, "ROOT inspector assumes legacy volumeID[6]")
    for count_name in ("unique", "unmapped", "ambiguous", "mismatched"):
        checks.require(count_name in inspector, f"ROOT inspector does not count {count_name} hits")
    for state in ("NOT_RUN", "FAIL", "PASS"):
        checks.require(state in runtime_validator, f"runtime validator lacks {state} state")


def check_bounded_and_nonproduction(checks: Checks) -> None:
    operational_files = (
        "magiccube_step4_job.sh",
        "magiccube_runtime_geometry_check.mac",
        "magiccube_runtime_system.mac",
        "magiccube_runtime_physics.mac",
        "run_magiccube_step4_runtime.py",
        "inspect_magiccube_runtime.py",
        "validate_magiccube_runtime.py",
    )
    combined = "\n".join(read_text(name) for name in operational_files)
    checks.require("/user/tridevme" not in combined and "/vscratch/grp-rutaoyao/Tridev" not in combined, "Step-4 files contain a stale Tridev path")
    for token in ("source_grid", "2500 source", "system_matrix", "mlem"):
        checks.require(token not in combined.lower(), f"Step-4 operational code contains forbidden production work: {token}")

    for name in ("run_magiccube_step4_runtime.py", "inspect_magiccube_runtime.py", "validate_magiccube_runtime.py"):
        tree = ast.parse(read_text(name), filename=name)
        checks.require(not any(isinstance(node, ast.While) for node in ast.walk(tree)), f"{name} contains a suspicious while loop")
        function_names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for function in (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in {"run_gate", "main"}
        ):
            recursive = any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == function.name
                for child in ast.walk(function)
            )
            checks.require(not recursive, f"{name}:{function.name} recursively calls itself")
        checks.require(bool(function_names), f"{name} has no auditable function structure")


def main() -> int:
    checks = Checks()
    check_required_files(checks)
    if checks.failures:
        print("Magic-Cube Step-4 preparation validation: FAIL")
        for failure in checks.failures:
            print(f"- {failure}")
        return 1

    check_frozen_maps(checks)
    check_job(checks)
    check_runtime_macros(checks)
    check_probe_and_source_design(checks)
    check_inspector_and_runtime_validator(checks)
    check_bounded_and_nonproduction(checks)

    if checks.failures:
        print("Magic-Cube Step-4 preparation validation: FAIL")
        for failure in checks.failures:
            print(f"- {failure}")
        return 1
    print("Magic-Cube Step-4 preparation validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
