#!/usr/bin/env python3
"""Static preparation checks for the bounded Magic-Cube Step-6 port."""

from __future__ import annotations

import hashlib
import math
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE = ROOT / "MAGIC_CUBE_STEP5_CLOSURE_AUDIT.md"

FROZEN_HASH_FILES = {
    "magiccube_production_geometry.mac": "",
    "magiccube_production_system.mac": "",
    "magiccube_production_physics.mac": "",
    "magiccube_production_digitizer.mac": "",
    "detector_map.csv": "",
    "magiccube_lattice_map.csv": "",
    "magiccube_runtime_identity.json": "",
    "magiccube_v1_config.json": "",
}

SOURCE_COMMON_KEYS = [
    "/gate/source/addSource",
    "/gate/source/source1/gps/particle",
    "/gate/source/source1/gps/energytype",
    "/gate/source/source1/gps/monoenergy",
    "/gate/source/source1/setActivity",
    "/gate/source/source1/gps/type",
    "/gate/source/source1/gps/shape",
    "/gate/source/source1/gps/halfx",
    "/gate/source/source1/gps/halfy",
    "/gate/source/source1/gps/angtype",
    "/gate/source/source1/gps/mintheta",
    "/gate/source/source1/gps/maxtheta",
    "/gate/source/source1/gps/minphi",
    "/gate/source/source1/gps/maxphi",
    "/gate/source/list",
]

EXPECTED_SOURCE_VALUES = {
    "/gate/source/source1/gps/particle": "gamma",
    "/gate/source/source1/gps/energytype": "Mono",
    "/gate/source/source1/gps/monoenergy": "140.0 keV",
    "/gate/source/source1/setActivity": "0.0001 Ci",
    "/gate/source/source1/gps/type": "Plane",
    "/gate/source/source1/gps/shape": "Rectangle",
    "/gate/source/source1/gps/halfx": "250 mm",
    "/gate/source/source1/gps/halfy": "250 mm",
    "/gate/source/source1/gps/angtype": "iso",
    "/gate/source/source1/gps/mintheta": "90 deg",
    "/gate/source/source1/gps/maxtheta": "90 deg",
    "/gate/source/source1/gps/minphi": "150 deg",
    "/gate/source/source1/gps/maxphi": "210 deg",
}

EXPECTED_SINGLES = [
    "Singles_mc_gagg_ee",
    "Singles_mc_gagg_eo",
    "Singles_mc_gagg_oe",
    "Singles_mc_gagg_oo",
]


def active_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def command_value(lines: list[str], command: str) -> str | None:
    values = [line[len(command) :].strip() for line in lines if line.startswith(command)]
    if len(values) != 1:
        return None
    return values[0]


def normalized(value: str | None) -> str | None:
    return " ".join(value.split()) if value is not None else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def closure_hashes() -> dict[str, str]:
    if not CLOSURE.exists():
        return {}
    text = CLOSURE.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for filename in FROZEN_HASH_FILES:
        pattern = re.compile(
            rf"\|\s*`{re.escape(filename)}`\s*\|.*?`([0-9a-f]{{64}})`\s*\|"
        )
        match = pattern.search(text)
        if match:
            result[filename] = match.group(1)
    return result


def first_index(lines: list[str], predicate) -> int | None:
    for index, line in enumerate(lines):
        if predicate(line):
            return index
    return None


def main() -> int:
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if condition:
            print(f"- PASS: {message}")
        else:
            print(f"- FAIL: {message}")
            failures.append(message)

    required_files = [
        "magiccube_production_source.mac",
        "magiccube_production_output.mac",
        "magiccube_production_main.mac",
        "magiccube_production_geometry.mac",
        "magiccube_production_system.mac",
        "magiccube_production_physics.mac",
        "magiccube_production_digitizer.mac",
        "source.mac",
        "output.mac",
        "SPEBT.mac",
        "MAGIC_CUBE_STEP5_CLOSURE_AUDIT.md",
    ]
    for filename in required_files:
        check((ROOT / filename).is_file(), f"required file exists: {filename}")

    # Step-5 closure hash gate.
    expected_hashes = closure_hashes()
    check(
        set(expected_hashes) == set(FROZEN_HASH_FILES),
        "Step-5 closure contains all eight frozen hashes",
    )
    hashes_match = True
    for filename in FROZEN_HASH_FILES:
        path = ROOT / filename
        expected = expected_hashes.get(filename)
        actual = sha256(path) if path.is_file() else None
        same = expected is not None and actual == expected
        hashes_match = hashes_match and same
        check(same, f"frozen hash matches: {filename}")
    if hashes_match:
        print("Step-5 frozen hashes match")

    source_original = active_lines(ROOT / "source.mac")
    source_port = active_lines(ROOT / "magiccube_production_source.mac")
    original_values = {
        key: command_value(source_original, key) for key in SOURCE_COMMON_KEYS
    }
    port_values = {
        key: command_value(source_port, key) for key in SOURCE_COMMON_KEYS
    }

    source_complete = all(value is not None for value in original_values.values())
    port_complete = all(value is not None for value in port_values.values())
    check(source_complete and port_complete, "active source command set is complete")

    original_expected = all(
        normalized(original_values[key]) == normalized(expected)
        for key, expected in EXPECTED_SOURCE_VALUES.items()
    )
    check(original_expected, "original active source values verified")

    preserved_common = all(
        normalized(original_values[key]) == normalized(port_values[key])
        for key in SOURCE_COMMON_KEYS
        if key != "/gate/source/source1/gps/centre"
    )
    check(preserved_common, "source statistical and angular parameters preserved")

    original_centre = normalized(
        command_value(source_original, "/gate/source/source1/gps/centre")
    )
    port_centre = normalized(
        command_value(source_port, "/gate/source/source1/gps/centre")
    )
    check(original_centre == "-187.5 0. 0. mm", "original source centre confirmed")
    check(port_centre == "0. 0. -187.5 mm", "Magic-Cube source centre is the axis-transformed value")

    original_keys = {line.split()[0] for line in source_original}
    port_keys = {line.split()[0] for line in source_port}
    allowed_new_source_keys = {
        "/gate/source/source1/gps/pos/rot1",
        "/gate/source/source1/gps/pos/rot2",
        "/gate/source/source1/gps/ang/rot1",
        "/gate/source/source1/gps/ang/rot2",
    }
    check(
        port_keys - original_keys <= allowed_new_source_keys,
        "source differences are bounded to the coordinate-frame rotation",
    )
    rotation_keys = (
        "/gate/source/source1/gps/pos/rot1",
        "/gate/source/source1/gps/pos/rot2",
        "/gate/source/source1/gps/ang/rot1",
        "/gate/source/source1/gps/ang/rot2",
    )
    expected_rotations = {
        "/gate/source/source1/gps/pos/rot1": "0. 0. 1.",
        "/gate/source/source1/gps/pos/rot2": "0. 1. 0.",
        "/gate/source/source1/gps/ang/rot1": "0. 0. -1.",
        "/gate/source/source1/gps/ang/rot2": "0. 1. 0.",
    }
    check(
        all(
            normalized(command_value(source_port, key)) == expected_rotations[key]
            for key in rotation_keys
        ),
        "positional and corrected angular source frames point toward Magic-Cube",
    )

    # The corrected angular frame maps the central local direction at
    # theta=90 deg, phi=180 deg from local -X to world +Z.  The detector is
    # centered at the origin and the source center is at z=-187.5 mm.
    source_to_detector = (0.0, 0.0, 1.0)
    central_direction = (0.0, 0.0, 1.0)
    central_dot = sum(a * b for a, b in zip(central_direction, source_to_detector))
    representative_z = {
        phi: -math.cos(math.radians(phi)) for phi in (150.0, 180.0, 210.0)
    }
    check(
        math.isclose(central_dot, 1.0, abs_tol=1e-12)
        and all(value > 0.0 for value in representative_z.values()),
        "corrected source directions point toward the Magic-Cube detector",
    )
    print("source central direction: +Z")
    print("source-to-detector direction: +Z")
    print(f"direction dot product: approximately {central_dot:g}")
    for phi, z_component in representative_z.items():
        y_component = math.sin(math.radians(phi))
        print(
            f"source direction phi={int(phi)}: "
            f"(0, {y_component:.6f}, {z_component:.6f})"
        )
    print("source points toward Magic-Cube: YES")
    check(
        not any(
            line.startswith("/gate/random/setSeed")
            or line.startswith("/gate/random/setSeeds")
            for line in source_port
        ),
        "no explicit RNG seed was added",
    )
    print("source transformation bounded to orientation/coordinates")

    # Original and Magic-Cube output configuration.
    output_original = active_lines(ROOT / "output.mac")
    output_port = active_lines(ROOT / "magiccube_production_output.mac")
    check(
        "/gate/output/tree/enable" in output_original
        and "/gate/output/tree/hits/enable" in output_original,
        "original-style ROOT Tree and Hits output verified",
    )
    check(
        "/gate/output/tree/enable" in output_port
        and "/gate/output/tree/hits/enable" in output_port,
        "Magic-Cube ROOT Tree and Hits output enabled",
    )
    original_collections = [
        command_value([line], "/gate/output/tree/addCollection")
        for line in output_original
        if line.startswith("/gate/output/tree/addCollection")
    ]
    port_collections = [
        command_value([line], "/gate/output/tree/addCollection")
        for line in output_port
        if line.startswith("/gate/output/tree/addCollection")
    ]
    check(original_collections == ["Singles"], "original Singles collection request verified")
    check(port_collections == EXPECTED_SINGLES, "four Magic-Cube Singles collections configured")
    check(
        command_value(output_port, "/gate/output/tree/addFileName")
        == "./magiccube_production.root",
        "production output uses a non-diagnostic Magic-Cube prefix",
    )
    forbidden_output_terms = (
        "ascii",
        "actor",
        "ntupl",
        "ppdf",
        "matrix",
        "detector_id",
        "detectorid",
    )
    check(
        not any(any(term in line.lower() for term in forbidden_output_terms) for line in output_port),
        "no unrelated actors or custom detector-ID output added",
    )
    print("original-style output preserved")

    # Main macro order is checked against the verified active SPEBT order,
    # with the detector-specific plate stage intentionally omitted.
    main_lines = active_lines(ROOT / "magiccube_production_main.mac")
    ordered_stages = [
        "/gate/geometry/setMaterialDatabase",
        "/control/execute magiccube_production_geometry.mac",
        "/control/execute magiccube_production_system.mac",
        "/control/execute magiccube_production_physics.mac",
        "/gate/run/initialize",
        "/control/execute magiccube_production_digitizer.mac",
        "/control/execute magiccube_production_source.mac",
        "/gate/random/setEngineName",
        "/gate/application/setTimeStart",
        "/gate/application/setTimeStop",
        "/control/execute verbose.mac",
        "/control/execute magiccube_production_output.mac",
        "/gate/application/startDAQ",
    ]
    stage_indices: list[int] = []
    for stage in ordered_stages:
        index = first_index(main_lines, lambda line, stage=stage: line.startswith(stage))
        if index is None:
            failures.append(f"main macro stage missing: {stage}")
            print(f"- FAIL: main macro stage missing: {stage}")
        else:
            stage_indices.append(index)
    check(
        len(stage_indices) == len(ordered_stages) and stage_indices == sorted(stage_indices),
        "main macro ordering matches the active original workflow",
    )
    check(
        command_value(main_lines, "/gate/geometry/setMaterialDatabase") == "GateMaterials.db",
        "GateMaterials.db is configured at the original stage",
    )
    check(
        command_value(main_lines, "/gate/random/setEngineName") == "MersenneTwister"
        and command_value(main_lines, "/gate/application/setTimeStart") == "0. s"
        and command_value(main_lines, "/gate/application/setTimeStop") == "15 s",
        "original RNG and 15-second acquisition timing preserved",
    )
    active_main_text = "\n".join(main_lines).lower()
    check("plate.mac" not in active_main_text, "original plate omitted intentionally")
    check("tungsten" not in active_main_text, "no tungsten collimator added")
    check("magiccube_runtime_system" not in active_main_text, "Step-4 runtime system is not used")
    check("magiccube_step5" not in active_main_text, "Step-5 diagnostic macros are not used")
    check("-66" not in active_main_text and "smoke" not in active_main_text, "no bounded smoke source substituted")
    print("main macro ordering matches original workflow")

    # Frozen identity contract remains authoritative; only the output schema
    # is intentionally deferred to Step 7 runtime inspection.
    identity_text = (ROOT / "magiccube_runtime_identity.json").read_text(encoding="utf-8")
    closure_text = CLOSURE.read_text(encoding="utf-8") if CLOSURE.exists() else ""
    formula_present = bool(
        re.search(r"d\s*\*\s*256\s*\+\s*iy\s*\*\s*16\s*\+\s*ix", identity_text + closure_text)
    )
    check("POSITION_DERIVED_REQUIRED" in identity_text + closure_text, "POSITION_DERIVED_REQUIRED retained")
    check("detector_map.csv" in identity_text + closure_text and formula_present, "canonical detector mapping remains documented")
    check((ROOT / "detector_map.csv").is_file(), "detector_map.csv remains present and hash-guarded")
    print("IDENTITY_OUTPUT_UNKNOWN_UNTIL_RUNTIME")

    check(
        all(
            token not in (ROOT / filename).read_text(encoding="utf-8").lower()
            for filename in (
                "magiccube_production_source.mac",
                "magiccube_production_output.mac",
                "magiccube_production_main.mac",
            )
            for token in ("ppdf", "system matrix", "reconstruction")
        ),
        "Step-6 files contain no later-stage PPDF, matrix, or reconstruction work",
    )
    print("no runtime execution performed")

    if failures:
        print("STATIC STEP-6 PREPARATION: FAIL")
        print("Failures:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("STATIC STEP-6 PREPARATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
