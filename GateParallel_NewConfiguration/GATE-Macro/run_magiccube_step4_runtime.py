#!/usr/bin/env python3
"""Run the bounded Magic-Cube Step-4 probes from a user-submitted compute job."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
DETECTOR_MAP = WORKDIR / "detector_map.csv"
OUTPUT_DIR = Path(
    "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step4"
)

PROBE_ENERGY_KEV = 30.0
SMOKE_ENERGY_KEV = 140.0
SMOKE_SOURCE_MM = (0.0, 0.0, -66.0)
PROBE_ACTIVITY_BQ = 100.0
SMOKE_ACTIVITY_BQ = 20_000.0
RUN_DURATION_S = 1.0

GAGG_FAMILIES = (
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
)
PROBE_COORDINATES = (
    (0, 0, 0),
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (7, 0, 0),
    (0, 7, 0),
    (0, 0, 7),
    (7, 7, 7),
)
RUNTIME_INPUT_FILES = (
    "GateMaterials.db",
    "magiccube_geometry.mac",
    "magiccube_runtime_system.mac",
    "magiccube_runtime_physics.mac",
)


def load_detector_map() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with DETECTOR_MAP.open(newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            rows.append(
                {
                    **raw,
                    "detector_id": int(raw["detector_id"]),
                    "ix": int(raw["ix"]),
                    "iy": int(raw["iy"]),
                    "d": int(raw["d"]),
                    "physical_layer_k": int(raw["physical_layer_k"]),
                    "x_mm": float(raw["x_mm"]),
                    "y_mm": float(raw["y_mm"]),
                    "z_mm": float(raw["z_mm"]),
                    "family_rx": int(raw["family_rx"]),
                    "family_ry": int(raw["family_ry"]),
                    "family_rz": int(raw["family_rz"]),
                }
            )
    return rows


def select_probes(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_family_coordinate = {
        (
            row["gate_family_name"],
            row["family_rx"],
            row["family_ry"],
            row["family_rz"],
        ): row
        for row in rows
    }
    probes: list[dict[str, object]] = []
    for family in GAGG_FAMILIES:
        for rx, ry, rz in PROBE_COORDINATES:
            key = (family, rx, ry, rz)
            if key not in by_family_coordinate:
                raise RuntimeError(f"detector_map.csv has no GAGG row for {key}")
            probes.append(dict(by_family_coordinate[key]))

    if len(probes) != 32 or len({p["detector_id"] for p in probes}) != 32:
        raise RuntimeError("fixed probe selection must contain 32 unique detectors")
    return probes


def prepare_runtime_inputs() -> None:
    """Copy fixed macro inputs beside generated macros to avoid spaced macro paths."""
    for name in RUNTIME_INPUT_FILES:
        source = WORKDIR / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, OUTPUT_DIR / name)


def render_run_macro(
    *,
    source_name: str,
    source_position_mm: tuple[float, float, float],
    energy_kev: float,
    activity_bq: float,
    root_file_name: str,
) -> str:
    x_mm, y_mm, z_mm = source_position_mm
    return f"""# Auto-generated bounded Magic-Cube Step-4 diagnostic run.
/gate/geometry/setMaterialDatabase GateMaterials.db
/gate/world/geometry/setXLength 200.0 mm
/gate/world/geometry/setYLength 200.0 mm
/gate/world/geometry/setZLength 200.0 mm
/gate/world/setMaterial Air
/control/execute magiccube_geometry.mac
/control/execute magiccube_runtime_system.mac
/control/execute magiccube_runtime_physics.mac
/gate/run/initialize

/gate/source/addSource {source_name} gps
/gate/source/{source_name}/gps/particle gamma
/gate/source/{source_name}/gps/pos/type Point
/gate/source/{source_name}/gps/pos/centre {x_mm:.9g} {y_mm:.9g} {z_mm:.9g} mm
/gate/source/{source_name}/gps/ang/type iso
/gate/source/{source_name}/gps/ene/type Mono
/gate/source/{source_name}/gps/ene/mono {energy_kev:.9g} keV
/gate/source/{source_name}/setActivity {activity_bq:.9g} becquerel

/gate/output/tree/enable
/gate/output/tree/addFileName {root_file_name}
/gate/output/tree/hits/enable

/gate/application/setTimeStart 0.0 s
/gate/application/setTimeStop {RUN_DURATION_S:.9g} s
/gate/application/setTimeSlice {RUN_DURATION_S:.9g} s
/gate/application/startDAQ
"""


def root_snapshot(stem: str) -> dict[Path, tuple[int, int]]:
    return {
        path: (path.stat().st_mtime_ns, path.stat().st_size)
        for path in OUTPUT_DIR.glob(f"{stem}*.root")
        if path.is_file()
    }


def run_gate(
    *,
    run_name: str,
    source_position_mm: tuple[float, float, float],
    energy_kev: float,
    activity_bq: float,
    expected: dict[str, object] | None,
) -> dict[str, object]:
    macro_path = OUTPUT_DIR / f"{run_name}.mac"
    root_file = OUTPUT_DIR / f"{run_name}.root"
    stdout_path = OUTPUT_DIR / f"{run_name}.stdout"
    stderr_path = OUTPUT_DIR / f"{run_name}.stderr"
    status_path = OUTPUT_DIR / f"{run_name}.status.json"

    macro_path.write_text(
        render_run_macro(
            source_name=run_name,
            source_position_mm=source_position_mm,
            energy_kev=energy_kev,
            activity_bq=activity_bq,
            root_file_name=root_file.name,
        ),
        encoding="utf-8",
    )
    before = root_snapshot(root_file.stem)
    with stdout_path.open("w", encoding="utf-8") as stdout_stream, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_stream:
        completed = subprocess.run(
            ["Gate", macro_path.name],
            cwd=OUTPUT_DIR,
            stdout=stdout_stream,
            stderr=stderr_stream,
            check=False,
        )

    after = root_snapshot(root_file.stem)
    current_roots = [
        path
        for path, metadata in after.items()
        if path not in before or before[path] != metadata
    ]
    result: dict[str, object] = {
        "run_name": run_name,
        "macro_path": str(macro_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "exit_code": completed.returncode,
        "root_output_requested": str(root_file),
        "root_files": [str(path) for path in sorted(current_roots)],
        "source": {
            "position_mm": list(source_position_mm),
            "energy_kev": energy_kev,
            "activity_bq": activity_bq,
            "duration_s": RUN_DURATION_S,
        },
        "expected": expected,
    }
    status_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if completed.returncode != 0:
        raise RuntimeError(
            f"{run_name}: Gate failed with exit code {completed.returncode}; "
            f"see {stderr_path}"
        )
    if not current_roots:
        raise RuntimeError(f"{run_name}: Gate returned success but created no current ROOT file")
    return result


def probe_manifest_row(index: int, probe: dict[str, object]) -> dict[str, object]:
    return {
        "probe_index": index,
        "run_name": f"probe_{index:02d}",
        "gate_family_name": probe["gate_family_name"],
        "family_rx": probe["family_rx"],
        "family_ry": probe["family_ry"],
        "family_rz": probe["family_rz"],
        "detector_id": probe["detector_id"],
        "ix": probe["ix"],
        "iy": probe["iy"],
        "d": probe["d"],
        "physical_layer_k": probe["physical_layer_k"],
        "x_mm": probe["x_mm"],
        "y_mm": probe["y_mm"],
        "z_mm": probe["z_mm"],
    }


def main() -> int:
    if shutil.which("Gate") is None:
        raise RuntimeError("Gate is not available in the compute-job PATH")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prepare_runtime_inputs()

    probes = select_probes(load_detector_map())
    manifest = [probe_manifest_row(index, probe) for index, probe in enumerate(probes)]
    (OUTPUT_DIR / "probe_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    completed_runs: list[dict[str, object]] = []
    for item in manifest:
        completed_runs.append(
            run_gate(
                run_name=str(item["run_name"]),
                source_position_mm=(
                    float(item["x_mm"]),
                    float(item["y_mm"]),
                    float(item["z_mm"]),
                ),
                energy_kev=PROBE_ENERGY_KEV,
                activity_bq=PROBE_ACTIVITY_BQ,
                expected=item,
            )
        )

    completed_runs.append(
        run_gate(
            run_name="smoke_140kev",
            source_position_mm=SMOKE_SOURCE_MM,
            energy_kev=SMOKE_ENERGY_KEV,
            activity_bq=SMOKE_ACTIVITY_BQ,
            expected=None,
        )
    )
    (OUTPUT_DIR / "runtime_run_summary.json").write_text(
        json.dumps(completed_runs, indent=2) + "\n", encoding="utf-8"
    )
    print("Magic-Cube Step-4 bounded runtime generation: COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
