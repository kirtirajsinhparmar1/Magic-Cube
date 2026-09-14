#!/usr/bin/env python3
"""Static safety checks for the Magic-Cube visualization export workflow."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEOMETRY = ROOT / "magiccube_geometry.mac"
FULL = ROOT / "magiccube_visualization.mac"
GAGG_ONLY = ROOT / "magiccube_visualization_gagg_only.mac"
JOB = ROOT / "magiccube_visualization_job.sh"
OUTDIR = "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/visualization"
WORKDIR = "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"
EXPECTED_GEOMETRY_SHA256 = "b2f6224e0cf129202edfc8e50c2677d967039689fbbfef4958208f0e5268001e"

GAGG_FAMILIES = ("mc_gagg_ee", "mc_gagg_eo", "mc_gagg_oe", "mc_gagg_oo")
K9_FAMILIES = ("mc_k9_ee", "mc_k9_eo", "mc_k9_oe", "mc_k9_oo")
REQUIRED_COPIES = (
    "GateMaterials.db",
    "magiccube_geometry.mac",
    "magiccube_visualization.mac",
    "magiccube_visualization_gagg_only.mac",
)

errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read_text(path: Path) -> str:
    require(path.is_file(), f"missing required file: {path.name}")
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def line_position(text: str, needle: str) -> int:
    return text.find(needle)


def check_visual_macro(path: Path) -> str:
    text = read_text(path)
    require("/gate/geometry/setMaterialDatabase GateMaterials.db" in text,
            f"{path.name}: GateMaterials.db is not configured")
    require(text.count("/control/execute magiccube_geometry.mac") == 1,
            f"{path.name}: frozen geometry must be executed exactly once")
    require("/vis/open VRML2FILE" in text,
            f"{path.name}: VRML2FILE is missing")
    initialize = line_position(text, "/gate/run/initialize")
    open_viewer = line_position(text, "/vis/open VRML2FILE")
    require(initialize >= 0 and open_viewer > initialize,
            f"{path.name}: visualization opens before GATE initialization")
    require("/gate/application/startDAQ" not in text,
            f"{path.name}: DAQ command is forbidden")
    require(not re.search(r"(?m)^\s*/(?:gate/)?source\b", text),
            f"{path.name}: particle source command is forbidden")
    require("/gate/physics/" not in text,
            f"{path.name}: physics configuration is forbidden")
    require("/gate/digitizer/" not in text,
            f"{path.name}: digitizer configuration is forbidden")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("/gate/") or "/vis/" in line:
            continue
        allowed = (
            line.startswith("/gate/geometry/setMaterialDatabase"),
            line.startswith("/gate/world/geometry/set"),
            line.startswith("/gate/world/setMaterial"),
            line.startswith("/gate/run/initialize"),
        )
        require(any(allowed), f"{path.name}: non-visual geometry command: {line}")
    return text


full_text = check_visual_macro(FULL)
gagg_only_text = check_visual_macro(GAGG_ONLY)

for family in GAGG_FAMILIES:
    require(f"/gate/{family}/vis/setColor red" in full_text,
            f"full macro: missing red GAGG color for {family}")
    require(f"/gate/{family}/vis/forceSolid" in full_text,
            f"full macro: missing solid GAGG setting for {family}")
    require(f"/gate/{family}/vis/setVisible 1" in full_text,
            f"full macro: missing visible GAGG setting for {family}")
    require(f"/gate/{family}/vis/setColor red" in gagg_only_text,
            f"GAGG-only macro: missing red GAGG color for {family}")

for family in K9_FAMILIES:
    require(f"/gate/{family}/vis/setColor blue" in full_text,
            f"full macro: missing blue K9 color for {family}")
    require(f"/gate/{family}/vis/forceSolid" in full_text,
            f"full macro: missing solid K9 setting for {family}")
    require(f"/gate/{family}/vis/setVisible 1" in full_text,
            f"full macro: missing visible K9 setting for {family}")
    require(f"/gate/{family}/vis/setVisible 0" in gagg_only_text,
            f"GAGG-only macro: K9 family {family} is not hidden")

for label, text in (("full", full_text), ("GAGG-only", gagg_only_text)):
    for axis in "XYZ":
        require(
            f"/gate/world/geometry/set{axis}Length 200.0 mm" in text,
            f"{label} macro: missing 200 mm world {axis}-length",
        )

require("/gate/world/vis/setVisible 0" in full_text,
        "full macro: world is not hidden")
require("/gate/magicCubeMother/vis/setVisible 0" in full_text,
        "full macro: mother is not hidden")
require("/gate/world/vis/setVisible 0" in gagg_only_text,
        "GAGG-only macro: world is not hidden")
require("/gate/magicCubeMother/vis/setVisible 0" in gagg_only_text,
        "GAGG-only macro: mother is not hidden")

job_text = read_text(JOB)
require("#SBATCH --cluster=ub-hpc" in job_text, "job: wrong cluster directive")
require("#SBATCH --partition=general-compute" in job_text, "job: wrong partition directive")
require("#SBATCH --qos=general-compute" in job_text, "job: wrong QOS directive")
require("#SBATCH --nodes=1" in job_text, "job: wrong node count")
require("#SBATCH --ntasks=1" in job_text, "job: wrong task count")
require("#SBATCH --cpus-per-task=1" in job_text, "job: wrong CPU count")
require("#SBATCH --mem=2G" in job_text, "job: wrong memory request")
require("#SBATCH --time=00:05:00" in job_text, "job: wrong wall time")
require(not re.search(r"(?m)^\s*#SBATCH\s+--array(?:=|\s)", job_text),
        "job: array submission is forbidden")
require(not re.search(r"(?m)^\s*(?:sbatch|srun|salloc)\b", job_text),
        "job: nested Slurm command is forbidden")
require('set -euo pipefail' in job_text, "job: strict shell mode is missing")
require(f'WORKDIR="{WORKDIR}"' in job_text, "job: WORKDIR is incorrect")
require(f'OUTDIR="{OUTDIR}"' in job_text, "job: OUTDIR is incorrect")
require("module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2" in job_text,
        "job: baseline Geant4 module pattern is missing")
require("module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2" in job_text,
        "job: GATE/OpenMPI module pattern is missing")
require('export GEANT4_DATA_DIR="$EBROOTGEANT4MINDATA"' in job_text,
        "job: GEANT4_DATA_DIR export is missing")
require('mkdir -p "$OUTDIR"' in job_text, "job: output directory is not created")
require('cd "$OUTDIR"' in job_text, "job: GATE is not run from OUTDIR")
for filename in REQUIRED_COPIES:
    require(f'cp -p "$WORKDIR/{filename}" "$OUTDIR/"' in job_text,
            f"job: required visualization input is not copied: {filename}")
require('export_one magiccube_visualization.mac magiccube_full.wrl' in job_text,
        "job: full export is missing")
require('export_one magiccube_visualization_gagg_only.mac magiccube_gagg_only.wrl' in job_text,
        "job: GAGG-only export is missing")
require('rm -f "$OUTDIR"/g4_*.wrl' in job_text,
        "job: raw VRML cleanup is not scoped to OUTDIR")
require('rm -f "$OUTDIR/magiccube_full.wrl"' in job_text,
        "job: full-output cleanup is missing")
require('rm -f "$OUTDIR/magiccube_gagg_only.wrl"' in job_text,
        "job: GAGG-only-output cleanup is missing")

require((ROOT / "GateMaterials.db").is_file(), "GateMaterials.db is missing")
require(GEOMETRY.is_file(), "frozen geometry file is missing")
if GEOMETRY.is_file():
    digest = hashlib.sha256(GEOMETRY.read_bytes()).hexdigest()
    require(digest == EXPECTED_GEOMETRY_SHA256,
            "frozen magiccube_geometry.mac SHA-256 changed")
    require("cubicArray/autoCenter false" in GEOMETRY.read_text(encoding="utf-8"),
            "frozen geometry does not contain the validated autoCenter false contract")

if errors:
    print("Magic-Cube visualization preparation: FAIL")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print("Magic-Cube visualization preparation: PASS")
print(f" - frozen geometry SHA-256: {EXPECTED_GEOMETRY_SHA256}")
print(" - both macros execute magiccube_geometry.mac exactly once")
print(" - VRML2FILE ordering, no source, no physics, and no DAQ verified")
print(" - full GAGG+K9 and GAGG-only visibility contracts verified")
print(" - non-array job, module pattern, copy set, and dedicated OUTDIR verified")
