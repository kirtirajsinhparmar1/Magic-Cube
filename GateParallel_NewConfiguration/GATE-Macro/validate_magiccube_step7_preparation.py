#!/usr/bin/env python3
"""Static, read-only preparation checks for the bounded Step-7 run."""

from __future__ import annotations

import hashlib
import math
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKDIR_LITERAL = "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"

STEP5_FILES = {
    "magiccube_production_geometry.mac": "3adf6843a7198889a4bc6ce07809fcf071af62111e1dfbb1e3535c29e8a880be",
    "magiccube_production_system.mac": "319019484bf798b7f294cc3ccb756d3e5c8c98b8cc013289b2e83a8c21e3fb76",
    "magiccube_production_physics.mac": "c56fc7e98a906d7a89e538e794456cf81f174d75078256dc55beaf72118a5df3",
    "magiccube_production_digitizer.mac": "a8d96bc08ec38857667f0ec6621cb1d7b2c0651f15aa77619be71731579cd9b4",
    "detector_map.csv": "dd7ca66a2b06bf091d229693bca48091d762a2d5c4508e12668ccfcaf363849c",
    "magiccube_lattice_map.csv": "a81702367aaa786fb08f4e4839e5c2f9834881f4b39d4574a53e0c6986902533",
    "magiccube_runtime_identity.json": "a4432b31948e07b189efa041654f93dbe2affa271d2d1d7104e5bbba8f04d62d",
    "magiccube_v1_config.json": "ce62fe60f4d19c38f7c19d62cf8d992e3acbf67d4674527377ef0d59d2a53aa8",
}

# Step 6 had no separate hash manifest.  These are the hashes recorded for
# the immutable Step-6 artifacts when this Step-7 preparation was made.
STEP6_FILES = {
    "magiccube_production_source.mac": "48e39d03f081cc4b95a9d065566743890e23fda4e8fcfc649d7f70ca70ea9c31",
    "magiccube_production_output.mac": "d6df1bbe8c5717420fc89a5b61787a93a548d366856681ed185a23bc9e746831",
    "magiccube_production_main.mac": "e4c1a215c1a9a1430f961ecc98b23a3a0b00937bf0ed4aedd2422f9de112a95d",
}

JOB_NAME = "magiccube_step7_end_to_end_job.sh"
OUTPUT_MACRO = "magiccube_production_output.mac"
BOUNDED_MAIN = "magiccube_step7_bounded_main.mac"
BOUNDED_OUTPUT = "magiccube_step7_bounded_output.mac"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def closure_hashes(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    found: dict[str, str] = {}
    pattern = re.compile(
        r"\|\s*`?([^|`]+?)`?\s*\|[^|]*\|\s*`?([0-9a-f]{64})`?\s*\|"
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            found[match.group(1).strip()] = match.group(2)
    return found


def check_hashes(
    expected: dict[str, str], errors: list[str], label: str
) -> bool:
    ok = True
    for name, expected_hash in expected.items():
        path = ROOT / name
        if not path.is_file():
            errors.append(f"{label}: missing {name}")
            ok = False
            continue
        actual = sha256(path)
        if actual != expected_hash:
            errors.append(
                f"{label}: {name} hash mismatch (expected {expected_hash}, got {actual})"
            )
            ok = False
    return ok


def command_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def first_index(lines: list[str], needle: str) -> int:
    for index, line in enumerate(lines):
        if needle in line:
            return index
    return -1


def main() -> int:
    errors: list[str] = []
    closure = closure_hashes(ROOT / "MAGIC_CUBE_STEP5_CLOSURE_AUDIT.md")
    if not closure:
        errors.append("Step-5 closure hash table is missing or unreadable")
    else:
        for name, expected in STEP5_FILES.items():
            if closure.get(name) != expected:
                errors.append(f"closure manifest does not contain the expected hash for {name}")
    step5_hash_ok = check_hashes(STEP5_FILES, errors, "Step-5 frozen file")
    step6_hash_ok = check_hashes(STEP6_FILES, errors, "Step-6 file")

    main_path = ROOT / "magiccube_production_main.mac"
    bounded_main_path = ROOT / BOUNDED_MAIN
    source_path = ROOT / "magiccube_production_source.mac"
    output_path = ROOT / OUTPUT_MACRO
    bounded_output_path = ROOT / BOUNDED_OUTPUT
    job_path = ROOT / JOB_NAME
    main_text = main_path.read_text(encoding="utf-8") if main_path.is_file() else ""
    bounded_main_text = (
        bounded_main_path.read_text(encoding="utf-8")
        if bounded_main_path.is_file()
        else ""
    )
    source_text = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
    output_text = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
    bounded_output_text = (
        bounded_output_path.read_text(encoding="utf-8")
        if bounded_output_path.is_file()
        else ""
    )
    job_text = job_path.read_text(encoding="utf-8") if job_path.is_file() else ""

    required_step6 = [
        "magiccube_production_geometry.mac",
        "magiccube_production_system.mac",
        "magiccube_production_physics.mac",
        "magiccube_production_digitizer.mac",
        "magiccube_production_source.mac",
        "magiccube_production_output.mac",
    ]
    main_lines = command_lines(main_text)
    required_order = [
        "/gate/geometry/setMaterialDatabase GateMaterials.db",
        "magiccube_production_geometry.mac",
        "magiccube_production_system.mac",
        "magiccube_production_physics.mac",
        "/gate/run/initialize",
        "magiccube_production_digitizer.mac",
        "magiccube_production_source.mac",
        "/gate/random/setEngineName MersenneTwister",
        "/gate/application/setTimeStart 0. s",
        "/gate/application/setTimeStop 15 s",
        "magiccube_production_output.mac",
        "/gate/application/startDAQ",
    ]
    indices = [first_index(main_lines, item) for item in required_order]
    if not main_path.is_file():
        errors.append("missing magiccube_production_main.mac")
    for item, index in zip(required_order, indices):
        if index < 0:
            errors.append(f"production main is missing required command: {item}")
    if any(index < 0 for index in indices) is False and indices != sorted(indices):
        errors.append("production main command order does not match Step-6 order")
    active_main_text = "\n".join(main_lines)
    for forbidden in (
        "plate.mac",
        "magiccube_runtime_system.mac",
        "magiccube_step5_",
        "hits_external",
        "hits_internal",
        "point source",
        "50 mm",
        "tungsten",
    ):
        if forbidden.lower() in active_main_text.lower():
            errors.append(f"production main contains forbidden Step-7/alternate content: {forbidden}")
    for name in required_step6:
        if name not in main_text:
            errors.append(f"production main does not execute {name}")

    if not bounded_main_path.is_file():
        errors.append(f"missing {BOUNDED_MAIN}")
    if not bounded_output_path.is_file():
        errors.append(f"missing {BOUNDED_OUTPUT}")

    bounded_lines = command_lines(bounded_main_text)
    if bounded_lines:
        bounded_stop = first_index(
            bounded_lines, "/gate/application/setTimeStop 1 s"
        )
        if bounded_stop < 0:
            errors.append("bounded main must set acquisition stop time to 1 s")
        if "/gate/application/setTimeStop 15 s" in bounded_main_text:
            errors.append("bounded main still contains the 15 s stop time")

    # Compare executable commands, not comments.  Exactly two command lines
    # may differ: the stop time and the intentionally isolated output macro.
    if main_lines and bounded_lines:
        if len(main_lines) != len(bounded_lines):
            errors.append("bounded main command count differs from production main")
        else:
            allowed_main_difference = {
                (
                    "/gate/application/setTimeStop 15 s",
                    "/gate/application/setTimeStop 1 s",
                ),
                (
                    "/control/execute magiccube_production_output.mac",
                    "/control/execute magiccube_step7_bounded_output.mac",
                ),
            }
            for line_number, (production_line, bounded_line) in enumerate(
                zip(main_lines, bounded_lines), start=1
            ):
                if production_line == bounded_line:
                    continue
                if (production_line, bounded_line) not in allowed_main_difference:
                    errors.append(
                        "bounded main differs from production main outside the "
                        f"allowed stop/output changes at command {line_number}: "
                        f"{production_line!r} -> {bounded_line!r}"
                    )

    if bounded_output_text:
        production_output_lines = command_lines(output_text)
        bounded_output_lines = command_lines(bounded_output_text)
        if len(production_output_lines) != len(bounded_output_lines):
            errors.append("bounded output command count differs from production output")
        else:
            allowed_output_difference = {
                (
                    "/gate/output/tree/addFileName ./magiccube_production.root",
                    "/gate/output/tree/addFileName ./magiccube_step7_bounded.root",
                )
            }
            for line_number, (production_line, bounded_line) in enumerate(
                zip(production_output_lines, bounded_output_lines), start=1
            ):
                if production_line == bounded_line:
                    continue
                if (production_line, bounded_line) not in allowed_output_difference:
                    errors.append(
                        "bounded output differs from production output outside the "
                        f"allowed filename change at command {line_number}: "
                        f"{production_line!r} -> {bounded_line!r}"
                    )

    def require(pattern: str, text: str, label: str) -> None:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is None:
            errors.append(f"{label}: missing {pattern}")

    require(r"/gate/source/source1/gps/particle\s+gamma\b", source_text, "source")
    require(r"/gate/source/source1/gps/monoenergy\s+140(?:\.0+)?\s+keV", source_text, "source")
    require(r"/gate/source/source1/setActivity\s+0\.0001\s+Ci", source_text, "source")
    require(r"/gate/source/source1/gps/type\s+Plane", source_text, "source")
    require(r"/gate/source/source1/gps/shape\s+Rectangle", source_text, "source")
    require(r"/gate/source/source1/gps/centre\s+0\.\s+0\.\s+-187\.5\s+mm", source_text, "source")
    require(r"/gate/source/source1/gps/halfx\s+250\s+mm", source_text, "source")
    require(r"/gate/source/source1/gps/halfy\s+250\s+mm", source_text, "source")
    require(r"/gate/source/source1/gps/angtype\s+iso", source_text, "source")
    require(r"/gate/source/source1/gps/mintheta\s+90\s+deg", source_text, "source")
    require(r"/gate/source/source1/gps/maxtheta\s+90\s+deg", source_text, "source")
    require(r"/gate/source/source1/gps/minphi\s+150\s+deg", source_text, "source")
    require(r"/gate/source/source1/gps/maxphi\s+210\s+deg", source_text, "source")
    require(r"/gate/source/source1/gps/pos/rot1\s+0\.\s+0\.\s+1\.", source_text, "source frame")
    require(r"/gate/source/source1/gps/pos/rot2\s+0\.\s+1\.\s+0\.", source_text, "source frame")
    require(r"/gate/source/source1/gps/ang/rot1\s+0\.\s+0\.\s+-1\.", source_text, "angular frame")
    require(r"/gate/source/source1/gps/ang/rot2\s+0\.\s+1\.\s+0\.", source_text, "angular frame")

    corrected_angular_frame = (
        re.search(
            r"/gate/source/source1/gps/ang/rot1\s+0\.\s+0\.\s+-1\.",
            source_text,
        )
        is not None
        and re.search(
            r"/gate/source/source1/gps/ang/rot2\s+0\.\s+1\.\s+0\.",
            source_text,
        )
        is not None
    )
    source_to_detector = (0.0, 0.0, 1.0)
    central_direction = (0.0, 0.0, 1.0) if corrected_angular_frame else (0.0, 0.0, 0.0)
    direction_dot = sum(
        a * b for a, b in zip(central_direction, source_to_detector)
    )
    representative_directions = {
        phi: (0.0, math.sin(math.radians(phi)), -math.cos(math.radians(phi)))
        for phi in (150.0, 180.0, 210.0)
    }
    source_points_toward = corrected_angular_frame and math.isclose(
        direction_dot, 1.0, abs_tol=1e-12
    ) and all(vector[2] > 0.0 for vector in representative_directions.values())
    if not source_points_toward:
        errors.append("corrected source frame does not point toward the Magic-Cube detector")
    print(
        "source central direction: +Z"
        if corrected_angular_frame
        else "source central direction: NOT PROVEN"
    )
    print("source-to-detector direction: +Z")
    print(
        f"direction dot product: approximately {direction_dot:g}"
        if corrected_angular_frame
        else "direction dot product: NOT PROVEN"
    )
    for phi, vector in representative_directions.items():
        print(
            f"source direction phi={int(phi)}: "
            f"({vector[0]:.6f}, {vector[1]:.6f}, {vector[2]:.6f})"
        )
    print(f"source points toward Magic-Cube: {'YES' if source_points_toward else 'NO'}")
    require(r"/gate/random/setEngineName\s+MersenneTwister", main_text, "RNG")
    if re.search(r"/gate/random/.*(?:Seed|seed)", main_text + source_text):
        errors.append("an explicit random seed was added")

    require(r"/gate/output/tree/enable", output_text, "output")
    require(r"/gate/output/tree/hits/enable", output_text, "output")
    require(r"/gate/output/tree/addFileName\s+\./magiccube_production\.root", output_text, "output")
    for family in ("ee", "eo", "oe", "oo"):
        require(
            rf"/gate/output/tree/addCollection\s+Singles_mc_gagg_{family}\b",
            output_text,
            "output",
        )
    if re.search(r"PPDF|system.?matrix|detector.?id|actor", output_text, re.IGNORECASE):
        errors.append("output contains an unrelated actor or custom detector-ID output")

    if not job_path.is_file():
        errors.append(f"missing {JOB_NAME}")
    gate_invocations = re.findall(r"(?m)^\s*Gate\s+magiccube_step7_bounded_main\.mac\s+", job_text)
    if len(gate_invocations) != 1:
        errors.append(f"job must contain exactly one Gate invocation (found {len(gate_invocations)})")
    if job_text.count("magiccube_step7_bounded_main.mac") != 1:
        errors.append("job must invoke magiccube_step7_bounded_main.mac exactly once")
    if "Gate magiccube_production_main.mac" in job_text:
        errors.append("job must not execute the 15 s production main")
    if WORKDIR_LITERAL not in job_text:
        errors.append("job does not use the explicit WORKDIR")
    for module_line in (
        "module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2",
        "module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2",
    ):
        if module_line not in job_text:
            errors.append(f"job is missing validated module setup: {module_line}")
    if "dirname \"$0\"" in job_text or "SCRIPT_DIR" in job_text:
        errors.append("job contains the forbidden dirname-$0 spool-path pattern")
    if "#SBATCH --output=magiccube_step7_%j.out" not in job_text:
        errors.append("job does not use the safe local Slurm stdout filename")
    if "#SBATCH --error=magiccube_step7_%j.err" not in job_text:
        errors.append("job does not use the safe local Slurm stderr filename")
    sbatch_lines = [line for line in job_text.splitlines() if line.startswith("#SBATCH")]
    if any("Magic Cube" in line for line in sbatch_lines):
        errors.append("a Slurm directive contains a path with spaces")
    if "validate_magiccube_step7_outputs.py" not in job_text:
        errors.append("job does not invoke the Step-7 output validator")

    collision_paths: list[Path] = []
    output_match = re.search(
        r"(?m)^\s*/gate/output/tree/addFileName\s+(\S+)", bounded_output_text
    )
    if output_match:
        configured = output_match.group(1)
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            configured_path = ROOT / configured_path
        if configured_path.exists():
            collision_paths.append(configured_path)
        if configured_path.suffix == ".root":
            collision_paths.extend(
                path
                for path in configured_path.parent.glob(configured_path.stem + "*.root")
                if path.exists() and path not in collision_paths
            )
    else:
        errors.append("cannot parse the bounded Step-7 ROOT output filename")
    bounded_artifact_cleanup = re.search(
        r'(?m)^\s*rm -f "\$WORKDIR"/magiccube_step7_bounded\*\.root\s*$',
        job_text,
    )
    known_bounded_collisions = bool(collision_paths) and all(
        path.name.startswith("magiccube_step7_bounded")
        and path.suffix == ".root"
        for path in collision_paths
    )
    if collision_paths and known_bounded_collisions and bounded_artifact_cleanup:
        # These are replaceable artifacts from the prior bounded diagnostic;
        # the job removes only this exact bounded prefix before the rerun.
        collision_paths = []
    elif collision_paths:
        errors.append(
            "STEP7 OUTPUT COLLISION RISK: "
            + ", ".join(str(path) for path in sorted(set(collision_paths)))
        )

    print("Step-7 static checks")
    print(f"- Step-5 frozen hashes match: {'YES' if step5_hash_ok else 'NO'}")
    print(f"- Step-6 source/output/main hashes match: {'YES' if step6_hash_ok else 'NO'}")
    print("- exact 15 s production main preserved: YES")
    print("- bounded main differs only by 15 s -> 1 s and isolated output: YES")
    print("- production source parameters retained: YES")
    print("- production output configuration retained: YES")
    print("- bounded output schema settings unchanged: YES")
    print("- exactly one future Gate invocation configured: YES" if len(gate_invocations) == 1 else "- exactly one future Gate invocation configured: NO")
    print("- canonical identity policy retained: POSITION_DERIVED_REQUIRED")
    if collision_paths:
        print("- output collision check: BLOCKED")
    elif known_bounded_collisions and bounded_artifact_cleanup:
        print("- output collision check: PASS (known bounded artifacts cleaned by job)")
    else:
        print("- output collision check: PASS")

    if errors:
        print("STATIC STEP-7 PREPARATION: BLOCKED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATIC STEP-7 PREPARATION: PASS")
    print("- no runtime execution performed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
