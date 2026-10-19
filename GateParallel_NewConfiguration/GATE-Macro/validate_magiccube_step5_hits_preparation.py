#!/usr/bin/env python3
"""Static preparation checks for the bounded Step-5 raw-Hits diagnostics."""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

FROZEN_SHA256 = {
    "magiccube_production_geometry.mac": "3adf6843a7198889a4bc6ce07809fcf071af62111e1dfbb1e3535c29e8a880be",
    "magiccube_production_system.mac": "319019484bf798b7f294cc3ccb756d3e5c8c98b8cc013289b2e83a8c21e3fb76",
    "magiccube_production_physics.mac": "c56fc7e98a906d7a89e538e794456cf81f174d75078256dc55beaf72118a5df3",
    "magiccube_production_digitizer.mac": "a8d96bc08ec38857667f0ec6621cb1d7b2c0651f15aa77619be71731579cd9b4",
    "detector_map.csv": "dd7ca66a2b06bf091d229693bca48091d762a2d5c4508e12668ccfcaf363849c",
}

GAGG_FAMILIES = (
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
)

PROBE_COORDINATES = {
    "mc_gagg_ee": (-31.5, -31.5, -15.0),
    "mc_gagg_eo": (-31.5, -27.3, -13.0),
    "mc_gagg_oe": (-27.3, -31.5, -13.0),
    "mc_gagg_oo": (-27.3, -27.3, -15.0),
}


def active_lines(path: Path) -> list[str]:
    return [
        line.split("#", 1)[0].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.split("#", 1)[0].strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_center(lines: list[str], source_name: str) -> tuple[float, float, float] | None:
    prefix = f"/gate/source/{source_name}/gps/pos/centre "
    for line in lines:
        if line.startswith(prefix):
            fields = line[len(prefix) :].split()
            if len(fields) >= 3:
                return tuple(float(value) for value in fields[:3])  # type: ignore[return-value]
    return None


def has_exact(lines: list[str], text: str) -> bool:
    return any(line == text for line in lines)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def verify_frozen_files(errors: list[str]) -> None:
    for name, expected in FROZEN_SHA256.items():
        path = ROOT / name
        require(path.is_file(), f"missing frozen file: {name}", errors)
        if path.is_file():
            require(sha256(path) == expected, f"frozen file changed: {name}", errors)


def verify_detector_map(errors: list[str]) -> None:
    path = ROOT / "detector_map.csv"
    if not path.is_file():
        return
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    ids = sorted(int(row["detector_id"]) for row in rows)
    require(len(rows) == 2048, "detector_map.csv does not contain 2048 rows", errors)
    require(ids == list(range(2048)), "detector_map.csv IDs are not exactly 0..2047", errors)

    expected_map_keys = {
        (family, 0, 0, 0): coordinates
        for family, coordinates in PROBE_COORDINATES.items()
    }
    for row in rows:
        key = (
            row["gate_family_name"],
            int(row["family_rx"]),
            int(row["family_ry"]),
            int(row["family_rz"]),
        )
        if key in expected_map_keys:
            actual = (float(row["x_mm"]), float(row["y_mm"]), float(row["z_mm"]))
            require(
                actual == expected_map_keys[key],
                f"detector_map.csv center mismatch for {key}: {actual}",
                errors,
            )


def verify_no_digitizer_or_singles(path: Path, errors: list[str]) -> list[str]:
    lines = active_lines(path)
    lowered = "\n".join(lines).lower()
    require("digitizer" not in lowered, f"{path.name} contains an active digitizer command", errors)
    require("singles" not in lowered, f"{path.name} contains an active Singles command", errors)
    require(
        has_exact(lines, "/gate/output/tree/hits/enable"),
        f"{path.name} does not enable Hits output",
        errors,
    )
    return lines


def verify_internal(errors: list[str]) -> None:
    path = ROOT / "magiccube_step5_hits_internal.mac"
    require(path.is_file(), "missing internal Hits diagnostic macro", errors)
    if not path.is_file():
        return
    lines = verify_no_digitizer_or_singles(path, errors)
    for include in (
        "/control/execute magiccube_production_geometry.mac",
        "/control/execute magiccube_production_system.mac",
        "/control/execute magiccube_production_physics.mac",
    ):
        require(has_exact(lines, include), f"internal macro missing: {include}", errors)
    source_lines = [line for line in lines if line.startswith("/gate/source/addSource ")]
    require(len(source_lines) == 4, "internal diagnostic does not define exactly four probes", errors)
    for family, coordinates in PROBE_COORDINATES.items():
        source_name = f"internal_{family}"
        require(
            any(line == f"/gate/source/addSource {source_name} gps" for line in source_lines),
            f"internal probe missing for {family}",
            errors,
        )
        actual = source_center(lines, source_name)
        require(actual == coordinates, f"internal probe center mismatch for {family}", errors)
        require(
            has_exact(lines, f"/gate/source/{source_name}/gps/ene/mono 30.0 keV"),
            f"internal probe energy mismatch for {family}",
            errors,
        )
        require(
            has_exact(lines, f"/gate/source/{source_name}/gps/ang/type iso"),
            f"internal probe angular setup missing for {family}",
            errors,
        )
    require(has_exact(lines, "/gate/application/setTimeStop 1.0 s"), "internal duration is not 1 s", errors)
    require(has_exact(lines, "/gate/application/startDAQ"), "internal acquisition is missing", errors)


def verify_external(errors: list[str]) -> None:
    path = ROOT / "magiccube_step5_hits_external.mac"
    require(path.is_file(), "missing external Hits diagnostic macro", errors)
    if not path.is_file():
        return
    lines = verify_no_digitizer_or_singles(path, errors)
    for include in (
        "/control/execute magiccube_production_geometry.mac",
        "/control/execute magiccube_production_system.mac",
        "/control/execute magiccube_production_physics.mac",
    ):
        require(has_exact(lines, include), f"external macro missing: {include}", errors)
    source_lines = [line for line in lines if line.startswith("/gate/source/addSource ")]
    require(len(source_lines) == 1, "external diagnostic must define exactly one source", errors)
    source_name = "external_140kev_smoke"
    require(
        has_exact(lines, f"/gate/source/addSource {source_name} gps"),
        "external smoke source is missing",
        errors,
    )
    require(
        source_center(lines, source_name) == (0.0, 0.0, -66.0),
        "external smoke source position is not (0,0,-66) mm",
        errors,
    )
    require(
        has_exact(lines, f"/gate/source/{source_name}/gps/ene/mono 140.0 keV"),
        "external smoke source is not 140 keV",
        errors,
    )
    require(
        has_exact(lines, f"/gate/source/{source_name}/gps/ang/type iso"),
        "external smoke source is not isotropic",
        errors,
    )
    require(has_exact(lines, "/gate/application/setTimeStop 1.0 s"), "external duration is not 1 s", errors)
    require(has_exact(lines, "/gate/application/startDAQ"), "external acquisition is missing", errors)


def verify_job(errors: list[str]) -> None:
    path = ROOT / "magiccube_step5_hits_job.sh"
    require(path.is_file(), "missing bounded Hits job", errors)
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    require(
        'WORKDIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/mcsim/GateParallel_NewConfiguration/GATE-Macro"' in text,
        "job does not use the explicit WORKDIR",
        errors,
    )
    require(
        'OUTPUT_DIR="/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step5_hits"' in text,
        "job does not use the explicit OUTPUT_DIR",
        errors,
    )
    require("module load gcc/11.2.0 geant4/11.2.1 geant4-data/11.2" in text, "known Geant4 module load missing", errors)
    require("module load gcc/11.2.0 openmpi/4.1.1 gate/9.4 geant4-data/11.2" in text, "known Gate module load missing", errors)
    require("SCRIPT_DIR" not in text, "job contains the forbidden SCRIPT_DIR-from-$0 pattern", errors)
    require("#SBATCH --output=magiccube_step5_hits_%j.out" in text, "Slurm output is not local", errors)
    require("#SBATCH --error=magiccube_step5_hits_%j.err" in text, "Slurm error is not local", errors)
    gate_invocations = re.findall(r"(?m)^\s*Gate\s+", text)
    require(len(gate_invocations) == 2, f"job has {len(gate_invocations)} Gate invocations, expected 2", errors)
    require("magiccube_step5_hits_internal.mac" in text, "job does not run the internal macro", errors)
    require("magiccube_step5_hits_external.mac" in text, "job does not run the external macro", errors)
    require("internal_gate.log" in text and "external_gate.log" in text, "separate Gate logs missing", errors)
    require(
        "internal_gate_exit_code.txt" in text and "external_gate_exit_code.txt" in text,
        "separate Gate exit-code files missing",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    verify_frozen_files(errors)
    verify_detector_map(errors)
    verify_internal(errors)
    verify_external(errors)
    verify_job(errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("STATIC HITS-DIAGNOSTIC PREPARATION: BLOCKED")
        return 1

    print("- both Hits-only diagnostic macros exist")
    print("- internal probe coordinates match the validated Step-4 detector-map centers")
    print("- all four GAGG families are represented by internal probes")
    print("- external isotropic 140-keV source is at (0,0,-66) mm")
    print("- production geometry/system/physics are reused unchanged")
    print("- production digitizer is excluded from both diagnostics")
    print("- Hits output is enabled and Singles output is absent")
    print("- detector_map.csv is unchanged with canonical IDs 0..2047")
    print("- explicit WORKDIR and validated Gate module setup are present")
    print("- job contains exactly two sequential Gate invocations")
    print("- bounded runtime artifacts are separated by test")
    print("STATIC HITS-DIAGNOSTIC PREPARATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
