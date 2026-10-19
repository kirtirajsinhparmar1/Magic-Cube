#!/usr/bin/env python3
"""Fast static contract checker for the complete OneCube preparation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
MACRO_DIR = PROJECT_ROOT / "GATE-Macro"
SCRIPT_DIR = PROJECT_ROOT / "scripts"
SLURM_DIR = PROJECT_ROOT / "slurm"

failures: List[str] = []


def fail(message: str) -> None:
    failures.append(message)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as error:  # noqa: BLE001 - report all preparation failures
        fail(f"cannot read {path.relative_to(PROJECT_ROOT)}: {error}")
        return ""


def active_lines(path: Path) -> List[str]:
    return [
        line.strip()
        for line in read_text(path).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def contains_line(lines: Iterable[str], pattern: str) -> bool:
    expression = re.compile(pattern)
    return any(expression.search(line) for line in lines)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def close(value: Any, expected: float, tolerance: float = 1.0e-9) -> bool:
    try:
        return abs(float(value) - expected) <= tolerance
    except (TypeError, ValueError):
        return False


def check_inventory() -> None:
    required_files = [
        "README.md",
        "ONECUBE_SPEC.md",
        "ONECUBE_PIPELINE.md",
        "ONECUBE_RUNBOOK.md",
        "config/onecube_config.json",
        "GATE-Macro/GateMaterials.db",
        "GATE-Macro/geometry.mac",
        "GATE-Macro/plate.mac",
        "GATE-Macro/system.mac",
        "GATE-Macro/physics.mac",
        "GATE-Macro/digitizer.mac",
        "GATE-Macro/source.mac",
        "GATE-Macro/output.mac",
        "GATE-Macro/verbose.mac",
        "GATE-Macro/OneCube.mac",
        "scripts/inspect_root.py",
        "scripts/generate_ppdf.py",
        "scripts/generate_sysmat.py",
        "scripts/plot_response.py",
        "scripts/validate_preparation.py",
        "scripts/validate_runtime.py",
        "scripts/final_summary.py",
        "slurm/onecube_sim.slurm",
        "slurm/onecube_merge.slurm",
        "slurm/onecube_ppdf.slurm",
        "slurm/onecube_sysmat.slurm",
        "slurm/onecube_plot.slurm",
        "slurm/onecube_validate.slurm",
        "slurm/par_all.sh",
    ]
    require(PROJECT_ROOT.is_dir(), "OneCube directory is missing")
    for relative in required_files:
        require(
            (PROJECT_ROOT / relative).is_file(),
            f"required file is missing: {relative}",
        )
    for relative in (
        "runtime/sim",
        "runtime/merged",
        "runtime/logs",
        "results/ppdf",
        "results/system_matrix",
        "results/plots",
        "results/validation",
    ):
        require((PROJECT_ROOT / relative).is_dir(), f"required directory is missing: {relative}")


def check_config_and_materials() -> None:
    config_path = PROJECT_ROOT / "config" / "onecube_config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001
        fail(f"config is not valid JSON: {error}")
        return

    detector = config.get("detector", {})
    source = config.get("source", {})
    acquisition = config.get("acquisition", {})
    digitizer = config.get("digitizer", {})
    output = config.get("output", {})

    require(detector.get("count") == 1, "config detector.count must be 1")
    require(detector.get("detector_id") == 0, "config detector_id must be 0")
    require(detector.get("name") == "onecube_crystal", "config detector name is incorrect")
    require(detector.get("material") == "GAGG", "config detector material must be GAGG")
    for axis in ("x", "y", "z"):
        require(close(detector.get(f"{axis}_mm"), 0.0), f"config detector {axis} center is not zero")
    for axis in ("x", "y", "z"):
        require(close(detector.get(f"size_{axis}_mm"), 2.0), f"config detector {axis} size is not 2 mm")

    require(source.get("source_count") == 1, "config source_count must be 1")
    require(source.get("source_id") == 0, "config source_id must be 0")
    require(source.get("particle") == "gamma", "config particle must be gamma")
    require(close(source.get("energy_keV"), 140.0), "config source energy must be 140 keV")
    require(close(source.get("z_mm"), -51.0), "config source z must be -51 mm")
    require(source.get("angular_type") == "isotropic", "config source must be isotropic")
    require(close(source.get("activity_Ci"), 0.0001), "config activity_Ci must be 0.0001")
    require(close(source.get("activity_Bq"), 3700000.0), "config activity_Bq must be 3700000")
    require(close(source.get("surface_distance_mm"), 50.0), "config surface distance must be 50 mm")

    require(close(acquisition.get("start_s"), 0.0), "config acquisition start must be 0 s")
    require(close(acquisition.get("stop_s"), 1.0), "config acquisition stop must be 1 s")
    require(close(acquisition.get("duration_s"), 1.0), "config acquisition duration must be 1 s")
    require(close(digitizer.get("energy_resolution_fwhm"), 0.10), "config energy FWHM is incorrect")
    require(close(digitizer.get("reference_energy_keV"), 140.0), "config reference energy is incorrect")
    require(close(digitizer.get("spatial_resolution_fwhm_mm"), 1.0), "config spatial FWHM is incorrect")
    require(digitizer.get("spatial_confine") is True, "config spatial confinement must be true")
    require(close(digitizer.get("energy_window_min_keV"), 120.0), "config energy minimum is incorrect")
    require(close(digitizer.get("energy_window_max_keV"), 160.0), "config energy maximum is incorrect")
    require(output.get("detector_count") == 1, "config output detector_count must be 1")
    require(output.get("detector_ids") == [0], "config output detector_ids must be [0]")

    copied_db = MACRO_DIR / "GateMaterials.db"
    db_text = read_text(copied_db)
    require(bool(re.search(r"(?im)^\s*Air\s*:", db_text)), "GateMaterials.db is missing Air")
    require(bool(re.search(r"(?im)^\s*GAGG\s*:", db_text)), "GateMaterials.db is missing GAGG")
    original_db = REPO_ROOT / "GateParallel_NewConfiguration" / "GATE-Macro" / "GateMaterials.db"
    require(
        original_db.is_file() and copied_db.read_bytes() == original_db.read_bytes(),
        "OneCube GateMaterials.db is not an unchanged copy of the original database",
    )


def check_geometry() -> None:
    geometry_path = MACRO_DIR / "geometry.mac"
    lines = active_lines(geometry_path)
    text = "\n".join(lines)
    require(sum("setMaterial GAGG" in line for line in lines) == 1, "geometry must contain exactly one GAGG volume")
    require(sum("daughters/name onecube_crystal" in line for line in lines) == 1, "geometry must define onecube_crystal once")
    for axis in ("X", "Y", "Z"):
        require(
            contains_line(lines, rf"onecube_crystal/geometry/set{axis}Length\s+2\s+mm$"),
            f"onecube_crystal {axis} size is not 2 mm",
        )
    require(
        contains_line(lines, r"onecube_crystal/placement/setTranslation\s+0\s+0\s+0\s+mm$"),
        "onecube_crystal is not centered at the origin",
    )
    for name, size in (("panel", 8), ("module", 6), ("block", 4)):
        for axis in ("X", "Y", "Z"):
            require(
                contains_line(lines, rf"{name}/geometry/set{axis}Length\s+{size}\s+mm$"),
                f"{name} {axis} size is not {size} mm",
            )
    require("setMaterial Air" in text, "geometry does not assign Air to bookkeeping volumes")
    for forbidden in ("K9", "tungsten", "MetalPlate", "SiPM", "repeat", "cubicArray", "xlayer"):
        require(forbidden.lower() not in text.lower(), f"geometry contains forbidden {forbidden}")

    plate_lines = active_lines(MACRO_DIR / "plate.mac")
    require(not plate_lines, "plate.mac must contain no active geometry commands")


def check_system_and_physics() -> None:
    system_lines = active_lines(MACRO_DIR / "system.mac")
    system_text = "\n".join(system_lines)
    require(sum("systems/cylindricalPET/rsector/attach panel" in line for line in system_lines) == 1, "rsector attachment is incorrect")
    require(sum("systems/cylindricalPET/module/attach module" in line for line in system_lines) == 1, "module attachment is incorrect")
    require(sum("systems/cylindricalPET/submodule/attach block" in line for line in system_lines) == 1, "submodule attachment is incorrect")
    require(sum("systems/cylindricalPET/crystal/attach onecube_crystal" in line for line in system_lines) == 1, "crystal attachment is incorrect")
    require(sum(re.search(r"/gate/onecube_crystal/attachCrystalSD\s*$", line) is not None for line in system_lines) == 1, "there must be one attachCrystalSD")
    require("attachCrystalSDnoSystem" not in system_text, "attachCrystalSDnoSystem is not allowed")
    require(sum(line == "/gate/systems/cylindricalPET/describe" for line in system_lines) == 1, "system describe command is missing")

    physics_lines = active_lines(MACRO_DIR / "physics.mac")
    physics_text = "\n".join(physics_lines)
    require(contains_line(physics_lines, r"addProcess\s+PhotoElectric$"), "PhotoElectric is not enabled")
    require(contains_line(physics_lines, r"PhotoElectric/setModel\s+StandardModel$"), "StandardModel is not selected")
    require(not contains_line(physics_lines, r"addProcess\s+Compton"), "Compton must be disabled")
    require(not contains_line(physics_lines, r"addProcess\s+Rayleigh"), "Rayleigh must be disabled")
    for particle in ("Gamma", "Electron", "Positron"):
        expected_cut = f"/gate/physics/{particle}/SetCutInRegion onecube_crystal 1.0 cm"
        require(expected_cut in physics_text, f"{particle} production cut is not 1.0 cm")


def check_digitizer_source_output() -> None:
    digitizer_lines = active_lines(MACRO_DIR / "digitizer.mac")
    insert_lines = [line for line in digitizer_lines if "/insert " in line]
    modules = [line.rsplit(" ", 1)[-1] for line in insert_lines]
    require(modules == ["adder", "energyResolution", "spatialResolution", "energyFraming"], "digitizer module order is incorrect")
    require(sum("/SinglesDigitizer/Singles/insert " in line for line in digitizer_lines) == 4, "digitizer must contain exactly one four-module Singles chain")
    digitizer_text = "\n".join(digitizer_lines)
    require("energyResolution/fwhm 0.10" in digitizer_text, "energy FWHM must be 0.10")
    require("energyOfReference 140 keV" in digitizer_text, "energy reference must be 140 keV")
    require("spatialResolution/fwhm 1.0 mm" in digitizer_text, "spatial FWHM must be 1.0 mm")
    require("confineInsideOfSmallestElement true" in digitizer_text, "spatial confinement must be true")
    require("energyFraming/setMin 120 keV" in digitizer_text and "energyFraming/setMax 160 keV", "energy framing must be 120-160 keV")
    require("Readout" not in digitizer_text and "DeadTime" not in digitizer_text and "PileUp" not in digitizer_text, "extra digitizer modules are not allowed")

    source_lines = active_lines(MACRO_DIR / "source.mac")
    source_text = "\n".join(source_lines)
    require(sum("addSource " in line for line in source_lines) == 1, "source.mac must define exactly one source")
    for required in (
        "/gate/source/source1/gps/particle gamma",
        "/gate/source/source1/gps/pos/type Point",
        "/gate/source/source1/gps/pos/centre 0 0 -51 mm",
        "/gate/source/source1/gps/ang/type iso",
        "/gate/source/source1/gps/ene/type Mono",
        "/gate/source/source1/gps/ene/mono 140 keV",
        "/gate/source/source1/setActivity 0.0001 Ci",
    ):
        require(required in source_text, f"source command missing: {required}")
    require(not any("rot" in line.lower() for line in source_lines), "source rotations are not allowed")
    require(source_lines[-1] == "/gate/source/list", "source list command must be last")

    output_lines = active_lines(MACRO_DIR / "output.mac")
    output_text = "\n".join(output_lines)
    require("/gate/output/tree/enable" in output_text, "ROOT Tree output is not enabled")
    require("/gate/output/tree/hits/enable" in output_text, "Hits output is not enabled")
    require("/gate/output/tree/addCollection Singles" in output_text, "shared Singles collection is not requested")
    require("OneCube/runtime/sim/onecube.root" in output_text, "output path is outside OneCube")


def check_main_macro() -> None:
    lines = active_lines(MACRO_DIR / "OneCube.mac")
    required_order = [
        "/gate/geometry/setMaterialDatabase GateMaterials.db",
        "/control/execute geometry.mac",
        "/control/execute plate.mac",
        "/control/execute system.mac",
        "/control/execute physics.mac",
        "/gate/run/initialize",
        "/control/execute digitizer.mac",
        "/control/execute source.mac",
        "/gate/random/setEngineName MersenneTwister",
        "/control/execute verbose.mac",
        "/control/execute output.mac",
        "/gate/application/setTimeStart 0 s",
        "/gate/application/setTimeStop 1 s",
        "/gate/application/setTimeSlice 1 s",
        "/gate/application/startDAQ",
    ]
    positions = []
    for command in required_order:
        require(command in lines, f"main macro command missing: {command}")
        if command in lines:
            positions.append(lines.index(command))
    require(positions == sorted(positions), "main macro stage order is incorrect")
    require(sum(line == "/gate/run/initialize" for line in lines) == 1, "main macro must initialize exactly once")
    require(sum(line == "/gate/application/startDAQ" for line in lines) == 1, "main macro must startDAQ exactly once")


def check_postprocessing_contract() -> None:
    files: List[Path] = list(MACRO_DIR.glob("*.mac"))
    files += [path for path in SCRIPT_DIR.glob("*.py") if path.name != "validate_preparation.py"]
    files += list(SLURM_DIR.glob("*"))
    bad_patterns = [
        (r"range\s*\(\s*144\b", "hard-coded range(144)"),
        (r"range\s*\(\s*2048\b", "hard-coded range(2048)"),
        (r"volumeID\s*\[\s*(?:2|6)\s*\]", "volumeID-index detector assumption"),
    ]
    for path in files:
        content = read_text(path)
        for pattern, label in bad_patterns:
            require(re.search(pattern, content) is None, f"{label} found in {path.relative_to(PROJECT_ROOT)}")
    config_text = read_text(PROJECT_ROOT / "config" / "onecube_config.json")
    require('"detector_ids": [0]' in config_text, "canonical detector ID 0 is not explicit")
    require('"source_id": 0' in config_text, "canonical source ID 0 is not explicit")
    sysmat_text = read_text(SCRIPT_DIR / "generate_sysmat.py")
    require("raw_singles_count" in sysmat_text, "system matrix does not preserve raw count")
    require("response_per_bq_s" in sysmat_text.lower(), "system matrix normalization formula is missing")
    require("matrix.shape != (1, 1)" in sysmat_text, "system matrix 1x1 shape enforcement is missing")


def check_shell_and_python() -> None:
    shell_files = list(SLURM_DIR.glob("*.sh")) + list(SLURM_DIR.glob("*.slurm"))
    for path in shell_files:
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        require(result.returncode == 0, f"bash -n failed for {path.relative_to(PROJECT_ROOT)}: {result.stderr.strip()}")

    for path in SCRIPT_DIR.glob("*.py"):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as error:
            fail(f"Python syntax failed for {path.relative_to(PROJECT_ROOT)}: {error}")


def check_slurm_contract() -> None:
    worker_files = sorted(SLURM_DIR.glob("onecube_*.slurm"))
    require(len(worker_files) == 6, "there must be six OneCube worker Slurm jobs")
    for path in worker_files:
        text = read_text(path)
        require("#SBATCH --partition=general-compute" in text, f"{path.name} has wrong partition")
        require("#SBATCH --qos=general-compute" in text, f"{path.name} has wrong QoS")
        require("Magic Cube/mcsim/OneCube" in text, f"{path.name} is missing the quoted OneCube path")
        require("sbatch" not in text, f"{path.name} must not submit nested jobs")
    sim_text = read_text(SLURM_DIR / "onecube_sim.slurm")
    merge_text = read_text(SLURM_DIR / "onecube_merge.slurm")
    for text, name in ((sim_text, "simulation"), (merge_text, "merge")):
        require("module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2" in text, f"{name} module setup is incomplete")
        require("export GEANT4_DATA_DIR=\"$EBROOTGEANT4MINDATA\"" in text, f"{name} GEANT4_DATA_DIR setup is incomplete")
        require("module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2" in text, f"{name} Gate module setup is incomplete")
    require("#SBATCH --array=0-0" in sim_text, "simulation array must be 0-0")
    require("Gate OneCube.mac" in sim_text, "simulation job must invoke Gate OneCube.mac")
    require("gate_exit_code.txt" in sim_text, "simulation job must record Gate exit code")

    python_jobs = ("onecube_ppdf.slurm", "onecube_sysmat.slurm", "onecube_plot.slurm", "onecube_validate.slurm")
    for name in python_jobs:
        require("env -u PYTHONPATH /user/kmparmar/venv/bin/python" in read_text(SLURM_DIR / name), f"{name} has wrong Python invocation")

    orchestrator = read_text(SLURM_DIR / "par_all.sh")
    require(orchestrator.count("sbatch --parsable") == 6, "par_all.sh must submit exactly six jobs")
    for dependency in (
        "onecube_merge.slurm",
        "onecube_ppdf.slurm",
        "onecube_sysmat.slurm",
        "onecube_plot.slurm",
        "onecube_validate.slurm",
    ):
        require(dependency in orchestrator, f"par_all.sh is missing {dependency}")
    require("afterok:" in orchestrator, "par_all.sh must use afterok dependencies")


def check_original_isolation() -> None:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
    )
    require(result.returncode == 0, f"could not inspect git isolation: {result.stderr.strip()}")
    outside = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("OneCube/")
    ]
    require(not outside, f"tracked changes exist outside OneCube: {outside}")


def main() -> int:
    check_inventory()
    check_config_and_materials()
    check_geometry()
    check_system_and_physics()
    check_digitizer_source_output()
    check_main_macro()
    check_postprocessing_contract()
    check_shell_and_python()
    check_slurm_contract()
    check_original_isolation()

    if failures:
        for message in failures:
            print(f"FAILED: {message}")
        print("ONECUBE STATIC PREPARATION: FAIL")
        return 1
    print("ONECUBE STATIC PREPARATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
