#!/usr/bin/env python3
"""Authoritative static-only Chunk-1 validator. Never invokes GATE or Slurm."""
from __future__ import annotations

import csv
import hashlib
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""


def number(row: dict[str, str], *names: str) -> float:
    for name in names:
        if name in row and row[name] != "":
            return float(row[name])
    raise KeyError("/".join(names))


check(ROOT.name == "MagicCubeFinal", "project root is not MagicCubeFinal")

# Bounded reference integrity evidence.
baseline_path = ROOT / "config/reference_baseline.json"
baseline = json.loads(read(baseline_path) or "{}")
for rel, expected in baseline.get("files", {}).items():
    path = REPO / rel
    check(path.is_file(), f"reference missing: {rel}")
    if path.is_file():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        check(actual == expected, f"reference modified: {rel}")

required = [
    "README.md", "MAGICCUBE_FINAL_SPEC.md", "MAGICCUBE_PIPELINE.md",
    "MAGICCUBE_RUNBOOK.md", "ASSUMPTIONS_AND_OPEN_ITEMS.md", "CHUNK1_BUILD_REPORT.md",
    "config/magiccube_config.json", "config/source_grid_config.json",
    "config/detector_map.csv", "config/validation_source_positions.csv",
    "GATE-Macro/GateMaterials.db", "GATE-Macro/geometry.mac", "GATE-Macro/plate.mac",
    "GATE-Macro/system.mac", "GATE-Macro/physics.mac", "GATE-Macro/digitizer.mac",
    "GATE-Macro/source.mac", "GATE-Macro/output.mac", "GATE-Macro/verbose.mac",
    "GATE-Macro/MagicCube.mac", "scripts/generate_detector_map.py",
    "scripts/generate_source_positions.py", "scripts/generate_simulation_manifest.py",
    "scripts/render_gate_macro.py", "scripts/inspect_root.py", "scripts/merge_runtime_outputs.py",
    "scripts/generate_ppdf.py", "scripts/generate_sysmat.py", "scripts/plot_positions.py",
    "scripts/plot_system_matrix.py", "scripts/validate_runtime.py", "scripts/final_summary.py",
    "slurm/magiccube_sim.slurm", "slurm/magiccube_merge.slurm", "slurm/magiccube_ppdf.slurm",
    "slurm/magiccube_sysmat.slurm", "slurm/magiccube_plot.slurm", "slurm/magiccube_validate.slurm",
    "slurm/par_validation.sh", "slurm/par_full.sh", "visualization/README.md",
]
for rel in required:
    check((ROOT / rel).is_file(), f"required file missing: {rel}")

# JSON parse and frozen configuration text checks.
configs = {}
for name in ("magiccube_config.json", "source_grid_config.json"):
    try:
        configs[name] = json.loads(read(ROOT / "config" / name))
    except Exception as exc:
        errors.append(f"invalid JSON config/{name}: {exc}")
config_blob = json.dumps(configs, sort_keys=True).lower()
for token, label in [
    ("67.2", "67.2 mm detector width"), ("32.0", "32 mm detector depth"),
    ("2048", "2048 detectors"), ("4.2", "4.2 mm lateral pitch"),
    ("100.0", "100 mm FOV"), ("2.0", "2 mm spacing/element"),
    ("-66.0", "-66 mm source plane"), ("140.0", "140 keV"),
]:
    check(token in config_blob, f"configuration missing {label}")
check("endpoint" in config_blob, "source-grid endpoint convention not explicit")
check("5916" in config_blob, "paper sensitivity target metadata missing")

# Detector map is the authoritative geometry/mapping artifact.
try:
    with (ROOT / "config/detector_map.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
except Exception as exc:
    rows = []
    errors.append(f"detector map unreadable: {exc}")
check(len(rows) == 2048, f"detector map rows {len(rows)} != 2048")
ids: list[int] = []
coords: list[tuple[float, float, float]] = []
for row in rows:
    try:
        did = int(row["detector_id"])
        ix, iy = int(row["ix"]), int(row["iy"])
        k = int(row.get("k") or row.get("iz") or row.get("depth_index") or row.get("physical_layer_k", ""))
        d = int(row.get("d", row.get("depth_pair_index", k // 2)))
        x, y, z = number(row, "x_mm"), number(row, "y_mm"), number(row, "z_mm")
        material = row.get("material") or row.get("gate_material_name", "")
        sensitive = row.get("is_sensitive", "true").lower() in {"1", "true", "yes"}
        check(did == d * 256 + iy * 16 + ix, f"mapping formula mismatch ID {did}")
        check(k == 2 * d + ((ix + iy) % 2), f"depth formula mismatch ID {did}")
        check((ix + iy + k) % 2 == 0, f"parity mismatch ID {did}")
        check(material.upper() == "GAGG" and sensitive, f"non-GAGG/non-sensitive mapped ID {did}")
        check(abs(x - (ix - 7.5) * 4.2) < 1e-8, f"x mismatch ID {did}")
        check(abs(y - (iy - 7.5) * 4.2) < 1e-8, f"y mismatch ID {did}")
        check(abs(z - (k - 7.5) * 2.0) < 1e-8, f"z mismatch ID {did}")
        check(-32.5 <= x <= 32.5 and -32.5 <= y <= 32.5 and -16 <= z <= 16, f"out-of-bounds ID {did}")
        ids.append(did); coords.append((x, y, z))
    except Exception as exc:
        errors.append(f"invalid detector-map row: {exc}")
check(ids == list(range(2048)), "detector IDs are not ordered contiguous 0..2047")
check(len(set(ids)) == len(ids), "duplicate detector IDs")
check(len(set(coords)) == len(coords), "duplicate detector coordinates")
check(16**3 == 4096 and sum((ix+iy+k)%2 == 0 for ix in range(16) for iy in range(16) for k in range(16)) == 2048,
      "conceptual lattice/material count mismatch")

# Validation source contract.
try:
    with (ROOT / "config/validation_source_positions.csv").open(newline="", encoding="utf-8") as fh:
        sources = list(csv.DictReader(fh))
except Exception as exc:
    sources = []
    errors.append(f"validation source table unreadable: {exc}")
check(len(sources) == 1, "validation source count is not one")
if sources:
    s = sources[0]
    try:
        check(int(s["source_id"]) == 0, "validation source ID is not 0")
        xyz = (number(s, "x_mm"), number(s, "y_mm"), number(s, "z_mm"))
        check(xyz == (0.0, 0.0, -66.0), f"validation source position is {xyz}")
        check(abs((-16.0) - xyz[2] - 50.0) < 1e-12, "source-to-front-surface distance is not 50 mm")
        check(number(s, "energy_keV", "energy_kev") == 140.0, "validation energy is not 140 keV")
        check(s.get("angular_distribution", s.get("direction", "")).lower() == "isotropic", "source is not isotropic")
        check(number(s, "activity_bq", "activity_Bq") == 3.7e6, "activity is not 3.7e6 Bq")
        check(number(s, "acquisition_s", "acquisition_time_s") == 1.0, "acquisition is not 1 s")
    except Exception as exc:
        errors.append(f"validation source schema/value error: {exc}")

geometry = read(ROOT / "GATE-Macro/geometry.mac")
system = read(ROOT / "GATE-Macro/system.mac")
physics = read(ROOT / "GATE-Macro/physics.mac")
digitizer = read(ROOT / "GATE-Macro/digitizer.mac")
source_macro = read(ROOT / "GATE-Macro/source.mac")
output = read(ROOT / "GATE-Macro/output.mac")
materials = read(ROOT / "GATE-Macro/GateMaterials.db")
all_macros = "\n".join(read(p) for p in (ROOT / "GATE-Macro").glob("*.mac"))
check("cylindricalPET" in geometry + system, "cylindricalPET hierarchy missing")
check(system.count("attachCrystalSD") >= 4 and "attachCrystalSDnoSystem" not in system, "ordinary four-family sensitive attachment missing")
check("mc_k9" not in "\n".join(line for line in system.splitlines() if "attachCrystalSD" in line), "K9 marked sensitive")
check("K9_V1_PROXY" in materials, "K9 proxy missing")
check("PhotoElectric" in physics and "StandardModel" in physics, "PhotoElectric StandardModel missing")
active_physics = "\n".join(line for line in physics.splitlines() if not line.lstrip().startswith("#"))
check("Compton" not in active_physics and "Rayleigh" not in active_physics, "Compton/Rayleigh active")
check(active_physics.count("1.0 cm") >= 3, "1 cm particle cuts missing")
for token in ("adder", "energyResolution", "spatialResolution", "energyFraming", "0.10", "1.0 mm", "confineInsideOfSmallestElement true"):
    check(token.lower() in digitizer.lower(), f"digitizer setting missing: {token}")
for family in ("mc_gagg_ee", "mc_gagg_eo", "mc_gagg_oe", "mc_gagg_oo"):
    check(f"/gate/digitizerMgr/{family}/SinglesDigitizer/Singles/" in digitizer,
          f"digitizer manager missing: {family}")
for value in (140, 120, 160):
    check(re.search(rf"\b{value}(?:\.0*)?\s+keV\b", digitizer, re.I) is not None, f"digitizer energy missing: {value} keV")
check("Point" in source_macro and "iso" in source_macro.lower() and "@Z_MM@" in source_macro, "point/isotropic/configured-position source template missing")
output_collections = [line.strip() for line in output.splitlines()
                      if line.strip().startswith("/gate/output/tree/addCollection")]
check(output_collections == ["/gate/output/tree/addCollection Singles"],
      "tree output must request exactly the common Singles collection")
check("/gate/output/tree/enable" in output and "/gate/output/tree/hits/enable" in output,
      "Hits/Singles tree output missing")

# Static code/shell checks.
for path in sorted(ROOT.rglob("*.py")):
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        errors.append(f"Python compile failed {path.relative_to(ROOT)}: {exc}")
for path in sorted(list(ROOT.rglob("*.sh")) + list(ROOT.rglob("*.slurm"))):
    result = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
    check(result.returncode == 0, f"bash syntax failed {path.relative_to(ROOT)}: {result.stderr.strip()}")

production_files = ([p for p in (ROOT / "scripts").glob("*") if p.name != "validate_preparation.py"]
                    + list((ROOT / "slurm").glob("*")) + list((ROOT / "GATE-Macro").glob("*"))
                    + [p for p in (ROOT / "config").glob("*.json") if p.name != "reference_baseline.json"])
production_blob = "\n".join(read(p) for p in production_files if p.is_file() and p.suffix not in {".pyc", ".parquet"})
for pattern, label in [
    (r"range\(\s*144\s*\)", "range(144)"), (r"/vscratch/grp-rutaoyao/Tridev", "old Tridev path"),
    (r"volumeID\s*\[\s*[26]\s*\]\s*==", "blind volumeID detector interpretation"),
    (r"(?<!runID,\s)eventID\s*\]", "eventID-only join"),
]:
    check(re.search(pattern, production_blob) is None, f"forbidden pattern found: {label}")
check("-51" not in production_blob, "OneCube source position -51 found in production files")
check("/OneCube/" not in production_blob, "production path points into OneCube")

# Downstream and Slurm contracts are asserted textually without runtime execution.
ppdf = read(ROOT / "scripts/generate_ppdf.py")
sysmat = read(ROOT / "scripts/generate_sysmat.py")
merge = read(ROOT / "scripts/merge_runtime_outputs.py")
check("detector_map" in ppdf and "raw_singles_count" in ppdf and "ppdf" in ppdf.lower(), "PPDF all-detector/raw-count contract missing")
check("zero" in ppdf.lower() or "fill_value" in ppdf.lower() or "fillna" in ppdf.lower(), "PPDF zero-denominator handling not evident")
for token in ("system_matrix_raw_counts.npy", "system_matrix_cps_per_bq.npy", "raw_singles_count", "cps_per_bq", "cps_per_mbq"):
    check(token in sysmat, f"system-matrix contract missing: {token}")
check("replicate_id" in merge and "source_id" in merge, "merge does not preserve source/replicate context")
check("eventID" not in merge or "runID" in merge, "merge uses eventID without runID context")
for orchestrator in ("par_validation.sh", "par_full.sh"):
    text = read(ROOT / "slurm" / orchestrator)
    check("sbatch --parsable" in text and "afterok" in text and "simulation_manifest" in text, f"invalid orchestration: {orchestrator}")
for worker in (ROOT / "slurm").glob("*.slurm"):
    check("sbatch" not in read(worker), f"worker submits nested jobs: {worker.name}")
check("--array" in read(ROOT / "slurm/par_validation.sh") and "DictReader" in read(ROOT / "slurm/par_validation.sh"), "simulation array is not manifest-derived")

if errors:
    print("MAGICCUBE CHUNK1 STATIC PREPARATION: FAIL")
    for item in errors:
        print(f"- {item}")
    sys.exit(1)
print("MAGICCUBE CHUNK1 STATIC PREPARATION: PASS")
