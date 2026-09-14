#!/usr/bin/env python3
"""Static validation for the single centered cylindricalPET candidate."""

from __future__ import annotations

import csv
import hashlib
import math
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BODY_MARKER = "/gate/magicCubeMother/geometry/setXLength"
GAGG_FAMILIES = (
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
)
K9_FAMILIES = (
    "mc_k9_ee",
    "mc_k9_eo",
    "mc_k9_oe",
    "mc_k9_oo",
)
ALL_FAMILIES = (
    "mc_gagg_ee",
    "mc_k9_ee",
    "mc_gagg_eo",
    "mc_k9_eo",
    "mc_gagg_oe",
    "mc_k9_oe",
    "mc_gagg_oo",
    "mc_k9_oo",
)

# Frozen-file hashes captured before this bounded candidate was prepared.
EXPECTED_HASHES = {
    "magiccube_geometry.mac": "b2f6224e0cf129202edfc8e50c2677d967039689fbbfef4958208f0e5268001e",
    "magiccube_runtime_system.mac": "283e8cd6da288d8e1e36cf13e3a8b6767cc4b939017aa0a82a52e64a8925516c",
    "magiccube_runtime_physics.mac": "c7e1df4c6ac693649ef62a8350d473ddda92666ca8a027fbb8624c1a441b28ce",
    "magiccube_production_physics.mac": "c56fc7e98a906d7a89e538e794456cf81f174d75078256dc55beaf72118a5df3",
    "magiccube_production_digitizer.mac": "a8d96bc08ec38857667f0ec6621cb1d7b2c0651f15aa77619be71731579cd9b4",
    "detector_map.csv": "dd7ca66a2b06bf091d229693bca48091d762a2d5c4508e12668ccfcaf363849c",
    "magiccube_lattice_map.csv": "a81702367aaa786fb08f4e4839e5c2f9834881f4b39d4574a53e0c6986902533",
    "magiccube_runtime_identity.json": "a4432b31948e07b189efa041654f93dbe2affa271d2d1d7104e5bbba8f04d62d",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def detector_body(text: str) -> str | None:
    index = text.find(BODY_MARKER)
    return text[index:].strip() if index >= 0 else None


def line_values(text: str, pattern: str) -> list[str]:
    return re.findall(pattern, text, flags=re.MULTILINE)


def normalized_key(name: str) -> str:
    return name.strip().lower().replace("-", "_")


def family_blocks(text: str) -> dict[str, str]:
    matches = list(
        re.finditer(
            r"^/gate/magicCubeMother/daughters/name (mc_(?:gagg|k9)_[a-z]{2})\s*$",
            text,
            flags=re.MULTILINE,
        )
    )
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.start() : end]
    return blocks


def parse_float_tuple(block: str, pattern: str) -> tuple[float, ...] | None:
    match = re.search(pattern, block, flags=re.MULTILINE)
    if match is None:
        return None
    try:
        return tuple(float(value) for value in match.groups())
    except ValueError:
        return None


def expected_family_centers(text: str) -> dict[str, set[tuple[float, float, float]]]:
    centers: dict[str, set[tuple[float, float, float]]] = {}
    for family, block in family_blocks(text).items():
        base = parse_float_tuple(
            block,
            rf"^/gate/{re.escape(family)}/placement/setTranslation\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+mm$",
        )
        repeat_matches = dict(
            re.findall(
                rf"^/gate/{re.escape(family)}/cubicArray/setRepeatNumber([XYZ])\s+(\d+)$",
                block,
                flags=re.MULTILINE,
            )
        )
        vector = parse_float_tuple(
            block,
            rf"^/gate/{re.escape(family)}/cubicArray/setRepeatVector\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+mm$",
        )
        if base is None or vector is None or set(repeat_matches) != set("XYZ"):
            continue
        repeat = tuple(int(repeat_matches[axis]) for axis in "XYZ")
        centers[family] = {
            tuple(round(base[axis] + index[axis] * vector[axis], 6) for axis in range(3))
            for index in (
                (ix, iy, iz)
                for ix in range(repeat[0])
                for iy in range(repeat[1])
                for iz in range(repeat[2])
            )
        }
    return centers


def check_detector_map(production_geometry: str) -> str | None:
    path = ROOT / "detector_map.csv"
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        return f"detector_map.csv could not be read: {exc}"
    if not rows:
        return "detector_map.csv has no data rows"

    columns = {normalized_key(key): key for key in rows[0]}
    id_key = columns.get("detector_id")
    family_key = columns.get("gate_family_name")
    material_key = columns.get("gate_material_name")
    axis_keys = {
        axis: next(
            (
                columns[name]
                for name in (
                    f"{axis}_mm",
                    f"center_{axis}_mm",
                    f"centre_{axis}_mm",
                    f"global_{axis}_mm",
                    f"position_{axis}_mm",
                )
                if name in columns
            ),
            None,
        )
        for axis in "xyz"
    }
    if id_key is None or family_key is None or material_key is None or any(
        value is None for value in axis_keys.values()
    ):
        return "detector_map.csv lacks the required identity/material/coordinate columns"

    try:
        ids = sorted(int(row[id_key]) for row in rows)
    except (KeyError, TypeError, ValueError) as exc:
        return f"detector_map.csv detector IDs are not integers: {exc}"
    if ids != list(range(2048)):
        return "detector_map.csv detector IDs are not exactly 0..2047"

    expected = expected_family_centers(production_geometry)
    if set(expected) != set(ALL_FAMILIES):
        return "production geometry family definitions could not be parsed for center comparison"
    expected_gagg = {
        (family, center)
        for family in GAGG_FAMILIES
        for center in expected[family]
    }
    observed: set[tuple[str, tuple[float, float, float]]] = set()
    try:
        for row in rows:
            family = row[family_key]
            material = row[material_key]
            point = tuple(round(float(row[axis_keys[axis]]), 6) for axis in "xyz")
            if family not in GAGG_FAMILIES or material != "GAGG":
                return "detector_map.csv contains a non-GAGG detector row"
            if not all(math.isfinite(value) for value in point):
                return "detector_map.csv contains a non-finite detector center"
            observed.add((family, point))
    except (KeyError, TypeError, ValueError) as exc:
        return f"detector_map.csv contains invalid center data: {exc}"
    if len(observed) != 2048:
        return "detector_map.csv does not contain 2048 unique GAGG centers"
    if observed != expected_gagg:
        return "detector_map.csv centers do not match the unchanged production detector definitions"
    return None


def check() -> list[str]:
    errors: list[str] = []

    for name, expected in EXPECTED_HASHES.items():
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing frozen file: {name}")
        elif digest(path) != expected:
            errors.append(f"frozen file changed: {name}")
    if not (ROOT / "GateMaterials.db").is_file():
        errors.append("missing frozen material database: GateMaterials.db")

    geometry_path = ROOT / "magiccube_production_geometry.mac"
    system_path = ROOT / "magiccube_production_system.mac"
    harness_path = ROOT / "magiccube_step5_system_check.mac"
    job_path = ROOT / "magiccube_step5_system_job.sh"
    output_validator_path = ROOT / "validate_magiccube_step5_system_outputs.py"
    required_paths = (
        geometry_path,
        system_path,
        harness_path,
        job_path,
        output_validator_path,
    )
    for path in required_paths:
        if not path.is_file():
            errors.append(f"missing prepared file: {path.name}")
    if errors:
        return errors

    frozen_geometry = read("magiccube_geometry.mac")
    production_geometry = geometry_path.read_text(encoding="utf-8")
    frozen_body = detector_body(frozen_geometry)
    production_body = detector_body(production_geometry)
    if frozen_body is None or production_body is None:
        errors.append("production geometry is missing the Magic-Cube detector-body marker")
    elif production_body != frozen_body:
        errors.append("production geometry detector body does not exactly match frozen geometry")

    wrapper_lines = (
        "/gate/world/daughters/name cylindricalPET",
        "/gate/world/daughters/insert cylinder",
        "/gate/cylindricalPET/geometry/setRmin 0 mm",
        "/gate/cylindricalPET/geometry/setRmax 55 mm",
        "/gate/cylindricalPET/geometry/setHeight 42 mm",
        "/gate/cylindricalPET/setMaterial Air",
        "/gate/cylindricalPET/placement/setTranslation 0.0 0.0 0.0 mm",
        "/gate/cylindricalPET/daughters/name panel",
        "/gate/cylindricalPET/daughters/insert box",
        "/gate/panel/geometry/setXLength 73.2 mm",
        "/gate/panel/geometry/setYLength 73.2 mm",
        "/gate/panel/geometry/setZLength 38.0 mm",
        "/gate/panel/placement/setTranslation 0.0 0.0 0.0 mm",
        "/gate/panel/setMaterial Air",
        "/gate/panel/daughters/name module",
        "/gate/panel/daughters/insert box",
        "/gate/module/geometry/setXLength 71.2 mm",
        "/gate/module/geometry/setYLength 71.2 mm",
        "/gate/module/geometry/setZLength 36.0 mm",
        "/gate/module/placement/setTranslation 0.0 0.0 0.0 mm",
        "/gate/module/setMaterial Air",
        "/gate/module/daughters/name block",
        "/gate/module/daughters/insert box",
        "/gate/block/geometry/setXLength 69.2 mm",
        "/gate/block/geometry/setYLength 69.2 mm",
        "/gate/block/geometry/setZLength 34.0 mm",
        "/gate/block/placement/setTranslation 0.0 0.0 0.0 mm",
        "/gate/block/setMaterial Air",
        "/gate/block/daughters/name magicCubeMother",
        "/gate/block/daughters/insert box",
    )
    for line in wrapper_lines:
        if line not in production_geometry:
            errors.append(f"production wrapper is missing: {line}")
    for wrapper in ("cylindricalPET", "panel", "module", "block"):
        materials = line_values(
            production_geometry,
            rf"^/gate/{wrapper}/setMaterial\s+(\S+)$",
        )
        if materials != ["Air"]:
            errors.append(f"wrapper {wrapper} is not Air-only")
        if f"/gate/{wrapper}/vis/setVisible 0" not in production_geometry:
            errors.append(f"wrapper {wrapper} is not invisible")
    if "/gate/magicCubeMother/placement/setTranslation 0.0 0.0 0.0 mm" not in production_geometry:
        errors.append("magicCubeMother translation is not centered at zero")
    if "tungsten" in production_geometry.lower() or re.search(
        r"^/gate/xlayer", production_geometry, flags=re.MULTILINE
    ):
        errors.append("production geometry contains forbidden legacy detector structure")

    families = line_values(
        production_geometry,
        r"^/gate/magicCubeMother/daughters/name\s+(mc_(?:gagg|k9)_[a-z]{2})$",
    )
    if families != list(ALL_FAMILIES):
        errors.append("production geometry does not contain the exact eight frozen family names")
    if production_body is not None:
        map_error = check_detector_map(production_geometry)
        if map_error is not None:
            errors.append(map_error)

    system = system_path.read_text(encoding="utf-8")
    system_types = set(
        re.findall(r"^/gate/systems/([^/]+)/", system, flags=re.MULTILINE)
    )
    if system_types != {"cylindricalPET"}:
        errors.append("production system does not contain exactly one cylindricalPET strategy")
    attachments = re.findall(
        r"^/gate/systems/cylindricalPET/(rsector|module|submodule|crystal)/attach\s+(\S+)$",
        system,
        flags=re.MULTILINE,
    )
    if attachments != [
        ("rsector", "panel"),
        ("module", "module"),
        ("submodule", "block"),
        ("crystal", "magicCubeMother"),
    ]:
        errors.append("production system hierarchy is not panel -> module -> block -> magicCubeMother")
    targets = line_values(system, r"^/gate/([^/]+)/attachCrystalSD$")
    if targets != list(GAGG_FAMILIES):
        errors.append("production system does not target exactly the four GAGG families")
    if "attachCrystalSDnoSystem" in system:
        errors.append("production system contains attachCrystalSDnoSystem")
    if re.search(r"^/gate/mc_k9", system, flags=re.MULTILINE):
        errors.append("production system targets a K9 family")
    if system.count("/gate/systems/cylindricalPET/describe") != 1:
        errors.append("production system does not contain exactly one describe command")

    physics = read("magiccube_production_physics.mac")
    if "PhotoElectric" not in physics or "StandardModel" not in physics:
        errors.append("production physics no longer visibly contains PhotoElectric StandardModel")
    for forbidden in ("/Compton", "/Rayleigh"):
        if re.search(rf"^[^#\n]*{re.escape(forbidden)}", physics, flags=re.MULTILINE):
            errors.append(f"production physics has active forbidden process: {forbidden}")

    digitizer = read("magiccube_production_digitizer.mac")
    for family in GAGG_FAMILIES:
        prefix = f"/gate/digitizerMgr/{family}/SinglesDigitizer/Singles"
        required = (
            f"{prefix}/insert adder",
            f"{prefix}/insert energyResolution",
            f"{prefix}/energyResolution/fwhm 0.10",
            f"{prefix}/energyResolution/energyOfReference 140. keV",
            f"{prefix}/insert spatialResolution",
            f"{prefix}/spatialResolution/fwhm 1.0 mm",
            f"{prefix}/spatialResolution/confineInsideOfSmallestElement true",
            f"{prefix}/insert energyFraming",
            f"{prefix}/energyFraming/setMin 120. keV",
            f"{prefix}/energyFraming/setMax 160. keV",
        )
        for line in required:
            if line not in digitizer:
                errors.append(f"production digitizer missing unchanged command: {line}")
    if re.search(r"deadTime|pileUp|efficiency|coincidence", digitizer, flags=re.IGNORECASE):
        errors.append("production digitizer contains an out-of-scope extra module")

    harness = harness_path.read_text(encoding="utf-8")
    required_order = (
        "/control/execute magiccube_production_geometry.mac",
        "/control/execute magiccube_production_system.mac",
        "/control/execute magiccube_production_physics.mac",
        "/gate/run/initialize",
        "/control/execute magiccube_production_digitizer.mac",
    )
    positions = [harness.find(item) for item in required_order]
    if any(position < 0 for position in positions):
        errors.append("harness is missing a required production-stage command")
    elif positions != sorted(positions):
        errors.append("harness production-stage command order is invalid")
    for forbidden in (
        "/control/execute magiccube_geometry.mac",
        "/control/execute magiccube_runtime_system.mac",
    ):
        if forbidden in harness:
            errors.append(f"harness executes frozen Step-4 file: {forbidden}")
    for required in (
        "/gate/source/step5_system_smoke/gps/particle gamma",
        "/gate/source/step5_system_smoke/gps/ene/mono 140.0 keV",
        "/gate/source/step5_system_smoke/gps/pos/centre 0.0 0.0 -66.0 mm",
        "/gate/output/tree/enable",
        "/gate/output/tree/hits/enable",
        "/gate/output/tree/addCollection Singles",
    ):
        if required not in harness:
            errors.append(f"harness missing required bounded check setting: {required}")
    if len(re.findall(r"^/gate/application/startDAQ\s*$", harness, flags=re.MULTILINE)) != 1:
        errors.append("harness does not contain exactly one acquisition")

    job = job_path.read_text(encoding="utf-8")
    for required in (
        'WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"',
        "module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2",
        'export GEANT4_DATA_DIR="${EBROOTGEANT4MINDATA}"',
        "module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2",
        "#SBATCH --cluster=ub-hpc",
        "#SBATCH --partition=general-compute",
        "#SBATCH --qos=general-compute",
        "#SBATCH --time=00:10:00",
        "#SBATCH --output=magiccube_step5_system_%j.out",
        "#SBATCH --error=magiccube_step5_system_%j.err",
        'Gate "$WORKDIR/magiccube_step5_system_check.mac"',
        "validate_magiccube_step5_system_outputs.py",
    ):
        if required not in job:
            errors.append(f"job is missing required bounded-run setting: {required}")
    if "SCRIPT_DIR" in job:
        errors.append("job reintroduces SCRIPT_DIR instead of the explicit WORKDIR")

    output_validator = output_validator_path.read_text(encoding="utf-8")
    for required in (
        "--output-dir",
        "--gate-exit-code",
        "VALIDATOR ENVIRONMENT ERROR",
        "COMMAND NOT FOUND",
        "Failed to get the system corresponding to that digitizer",
    ):
        if required not in output_validator:
            errors.append(f"output validator missing required contract: {required}")

    identity = read("magiccube_runtime_identity.json")
    if "POSITION_DERIVED_REQUIRED" not in identity:
        errors.append("frozen identity policy is not POSITION_DERIVED_REQUIRED")

    return errors


def main() -> int:
    errors = check()
    if errors:
        print("STATIC PREPARATION: BLOCKED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("STATIC PREPARATION: PASS")
    print("- production cylindricalPET wrapper exists")
    print("- wrapper hierarchy is centered and Air-only")
    print("- production geometry detector body matches frozen geometry")
    print("- global Magic-Cube coordinates unchanged")
    print("- one cylindricalPET system candidate")
    print("- rsector -> panel")
    print("- module -> module")
    print("- submodule -> block")
    print("- crystal -> magicCubeMother")
    print("- four attachCrystalSD GAGG targets")
    print("- no K9 sensitive target")
    print("- production physics unchanged")
    print("- production digitizer unchanged")
    print("- detector_map.csv unchanged and centers compatible")
    print("- POSITION_DERIVED_REQUIRED retained")
    print("- bounded runtime harness prepared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
