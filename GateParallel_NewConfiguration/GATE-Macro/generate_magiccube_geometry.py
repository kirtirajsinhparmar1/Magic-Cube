#!/usr/bin/env python3
"""Generate deterministic Step-3 Magic-Cube geometry artifacts."""

import csv
import json
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "magiccube_v1_config.json"
LATTICE_MAP_PATH = BASE_DIR / "magiccube_lattice_map.csv"
DETECTOR_MAP_PATH = BASE_DIR / "detector_map.csv"
MACRO_PATH = BASE_DIR / "magiccube_geometry.mac"

FAMILY_NAMES = (
    "mc_gagg_ee",
    "mc_k9_ee",
    "mc_gagg_eo",
    "mc_k9_eo",
    "mc_gagg_oe",
    "mc_k9_oe",
    "mc_gagg_oo",
    "mc_k9_oo",
)

LATTICE_COLUMNS = (
    "lattice_linear_index", "ix", "iy", "k", "x_mm", "y_mm", "z_mm",
    "parity_3d", "material_concept", "gate_material_name", "ix_parity",
    "iy_parity", "gate_family_name", "family_rx", "family_ry", "family_rz",
    "family_local_index_conceptual", "detector_id", "d",
)

DETECTOR_COLUMNS = (
    "detector_id", "ix", "iy", "d", "physical_layer_k", "x_mm", "y_mm",
    "z_mm", "lattice_linear_index", "ix_parity", "iy_parity",
    "gate_family_name", "gate_material_name", "family_rx", "family_ry",
    "family_rz", "family_local_index_conceptual",
)


def fail(message):
    raise ValueError(f"Magic-Cube configuration contract failure: {message}")


def require_close(actual, expected, label):
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-9):
        fail(f"{label} is {actual!r}, expected {expected!r}")


def validate_config(config):
    lattice = config["lattice"]
    detector = config["detector"]
    counts = config["counts"]
    pattern = config["material_pattern"]
    materials = config["materials"]
    indexing = config["indexing"]
    for key in ("nx", "ny", "nz"):
        if lattice[key] != 16:
            fail(f"lattice.{key} must be 16")
    for axis, expected in (("x", 67.2), ("y", 67.2), ("z", 32.0)):
        require_close(detector["mother_size_mm"][axis], expected, f"mother size {axis}")
    for key, expected in (
        ("pitch_x_mm", 4.2), ("pitch_y_mm", 4.2),
        ("segment_size_x_mm", 2.0), ("segment_size_y_mm", 2.0),
        ("segment_size_z_mm", 2.0),
    ):
        require_close(lattice[key], expected, f"lattice.{key}")
    for key, expected in (
        ("total_lattice_positions", 4096), ("gagg_elements", 2048),
        ("k9_elements", 2048),
    ):
        if counts[key] != expected:
            fail(f"counts.{key} must be {expected}")
    if pattern["rule"] != "(ix + iy + k) % 2":
        fail("material_pattern.rule is not the frozen checkerboard rule")
    if pattern["gagg_when_remainder"] != 0 or pattern["k9_when_remainder"] != 1:
        fail("checkerboard material remainders must be GAGG=0 and K9=1")
    for material_key, expected in (("gagg", "GAGG"), ("k9", "K9_V1_PROXY"), ("air", "Air")):
        if materials[material_key]["gate_material_name"] != expected:
            fail(f"materials.{material_key}.gate_material_name must be {expected}")
    if indexing["detector_id"] != "d * 256 + iy * 16 + ix":
        fail("indexing.detector_id is not the frozen canonical formula")


def coordinate(value):
    return f"{float(value):.1f}"


def family_for(ix, iy, material):
    x_parity = "e" if ix % 2 == 0 else "o"
    y_parity = "e" if iy % 2 == 0 else "o"
    prefix = "mc_gagg_" if material == "GAGG" else "mc_k9_"
    return f"{prefix}{x_parity}{y_parity}"


def enumerate_rows(config):
    lattice = config["lattice"]
    rows = []
    detector_rows = []
    # k, iy, ix order is the explicit lattice_linear_index order.
    for k in range(lattice["nz"]):
        for iy in range(lattice["ny"]):
            for ix in range(lattice["nx"]):
                parity = (ix + iy + k) % 2
                material = "GAGG" if parity == 0 else "K9"
                gate_material = "GAGG" if material == "GAGG" else "K9_V1_PROXY"
                lattice_index = k * 256 + iy * 16 + ix
                x_mm = (ix - 7.5) * lattice["pitch_x_mm"]
                y_mm = (iy - 7.5) * lattice["pitch_y_mm"]
                z_mm = (k - 7.5) * lattice["segment_size_z_mm"]
                family_rx = ix // 2
                family_ry = iy // 2
                family_rz = k // 2
                family_local = family_rz * 64 + family_ry * 8 + family_rx
                family = family_for(ix, iy, material)
                detector_id = ""
                d_value = ""
                if material == "GAGG":
                    d_value = k // 2
                    if k != 2 * d_value + ((ix + iy) % 2):
                        fail(f"GAGG depth relation failed at {(ix, iy, k)}")
                    detector_id = d_value * 256 + iy * 16 + ix
                row = {
                    "lattice_linear_index": lattice_index, "ix": ix, "iy": iy,
                    "k": k, "x_mm": coordinate(x_mm), "y_mm": coordinate(y_mm),
                    "z_mm": coordinate(z_mm), "parity_3d": parity,
                    "material_concept": material, "gate_material_name": gate_material,
                    "ix_parity": "even" if ix % 2 == 0 else "odd",
                    "iy_parity": "even" if iy % 2 == 0 else "odd",
                    "gate_family_name": family, "family_rx": family_rx,
                    "family_ry": family_ry, "family_rz": family_rz,
                    "family_local_index_conceptual": family_local,
                    "detector_id": detector_id, "d": d_value,
                }
                rows.append(row)
                if material == "GAGG":
                    detector_rows.append({
                        "detector_id": detector_id, "ix": ix, "iy": iy, "d": d_value,
                        "physical_layer_k": k, "x_mm": coordinate(x_mm),
                        "y_mm": coordinate(y_mm), "z_mm": coordinate(z_mm),
                        "lattice_linear_index": lattice_index,
                        "ix_parity": "even" if ix % 2 == 0 else "odd",
                        "iy_parity": "even" if iy % 2 == 0 else "odd",
                        "gate_family_name": family, "gate_material_name": gate_material,
                        "family_rx": family_rx, "family_ry": family_ry,
                        "family_rz": family_rz,
                        "family_local_index_conceptual": family_local,
                    })
    if len(rows) != 4096 or len(detector_rows) != 2048:
        fail("enumeration counts do not match the frozen contract")
    return rows, sorted(detector_rows, key=lambda item: item["detector_id"])


def family_geometry(config):
    lattice = config["lattice"]
    x_start = {"e": -31.5, "o": -27.3}
    y_start = {"e": -31.5, "o": -27.3}
    families = []
    for suffix in ("ee", "eo", "oe", "oo"):
        x_parity, y_parity = suffix
        p = ((0 if x_parity == "e" else 1) + (0 if y_parity == "e" else 1)) % 2
        gagg_z = -15.0 if p == 0 else -13.0
        k9_z = -13.0 if p == 0 else -15.0
        for material, z_start in (("GAGG", gagg_z), ("K9_V1_PROXY", k9_z)):
            families.append({
                "name": f"mc_{'gagg' if material == 'GAGG' else 'k9'}_{suffix}",
                "ix_parity": "even" if x_parity == "e" else "odd",
                "iy_parity": "even" if y_parity == "e" else "odd",
                "material": material, "x_start": x_start[x_parity],
                "y_start": y_start[y_parity], "z_start": z_start,
                "repeat_x": lattice["nx"] // 2, "repeat_y": lattice["ny"] // 2,
                "repeat_z": lattice["nz"] // 2,
                "vector_x": lattice["pitch_x_mm"] * 2,
                "vector_y": lattice["pitch_y_mm"] * 2,
                "vector_z": lattice["segment_size_z_mm"] * 2,
            })
    return families


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_macro(config):
    detector = config["detector"]
    lattice = config["lattice"]
    lines = [
        "# AUTO-GENERATED FROM magiccube_v1_config.json",
        "# DO NOT HAND EDIT",
        "# Magic-Cube V1 detector geometry fragment",
        "# Runtime GATE copy-number mapping is NOT validated in Step 3",
        "",
        "/gate/world/daughters/name magicCubeMother",
        "/gate/world/daughters/insert box",
        f"/gate/magicCubeMother/geometry/setXLength {coordinate(detector['mother_size_mm']['x'])} mm",
        f"/gate/magicCubeMother/geometry/setYLength {coordinate(detector['mother_size_mm']['y'])} mm",
        f"/gate/magicCubeMother/geometry/setZLength {coordinate(detector['mother_size_mm']['z'])} mm",
        "/gate/magicCubeMother/setMaterial Air",
        "/gate/magicCubeMother/placement/setTranslation 0.0 0.0 0.0 mm",
        "",
        "# Family translations are frozen first-copy centers.",
        "# autoCenter false prevents GATE from treating them as repeated-array centers.",
        "",
    ]
    for family in family_geometry(config):
        name = family["name"]
        lines.extend([
            f"/gate/magicCubeMother/daughters/name {name}",
            "/gate/magicCubeMother/daughters/insert box",
            f"/gate/{name}/geometry/setXLength {coordinate(lattice['segment_size_x_mm'])} mm",
            f"/gate/{name}/geometry/setYLength {coordinate(lattice['segment_size_y_mm'])} mm",
            f"/gate/{name}/geometry/setZLength {coordinate(lattice['segment_size_z_mm'])} mm",
            f"/gate/{name}/setMaterial {family['material']}",
            f"/gate/{name}/placement/setTranslation {coordinate(family['x_start'])} {coordinate(family['y_start'])} {coordinate(family['z_start'])} mm",
            f"/gate/{name}/repeaters/insert cubicArray",
            f"/gate/{name}/cubicArray/autoCenter false",
            f"/gate/{name}/cubicArray/setRepeatNumberX {family['repeat_x']}",
            f"/gate/{name}/cubicArray/setRepeatNumberY {family['repeat_y']}",
            f"/gate/{name}/cubicArray/setRepeatNumberZ {family['repeat_z']}",
            f"/gate/{name}/cubicArray/setRepeatVector {coordinate(family['vector_x'])} {coordinate(family['vector_y'])} {coordinate(family['vector_z'])} mm",
            "",
        ])
    return "\n".join(lines)


def main():
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)
    validate_config(config)
    lattice_rows, detector_rows = enumerate_rows(config)
    write_csv(LATTICE_MAP_PATH, LATTICE_COLUMNS, lattice_rows)
    write_csv(DETECTOR_MAP_PATH, DETECTOR_COLUMNS, detector_rows)
    MACRO_PATH.write_text(generate_macro(config), encoding="utf-8")
    print("Generated deterministic Magic-Cube geometry artifacts:")
    print(f"  lattice rows: {len(lattice_rows)}")
    print(f"  detector rows: {len(detector_rows)}")
    print(f"  families: {len(family_geometry(config))}")


if __name__ == "__main__":
    main()
