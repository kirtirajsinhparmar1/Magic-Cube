#!/usr/bin/env python3
"""Independently validate the static Step-3 Magic-Cube artifacts."""

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
FAMILY_NAMES = (
    "mc_gagg_ee", "mc_k9_ee", "mc_gagg_eo", "mc_k9_eo",
    "mc_gagg_oe", "mc_k9_oe", "mc_gagg_oo", "mc_k9_oo",
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def close(actual, expected, message, tolerance=1e-9):
    check(math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance),
          f"{message}: {actual!r} != {expected!r}")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def integer(row, key):
    return int(row[key])


def number(row, key):
    return float(row[key])


def family_expected(config):
    lattice = config["lattice"]
    starts = {"e": -7.5 * lattice["pitch_x_mm"], "o": -6.5 * lattice["pitch_x_mm"]}
    y_starts = {"e": -7.5 * lattice["pitch_y_mm"], "o": -6.5 * lattice["pitch_y_mm"]}
    expected = {}
    for suffix in ("ee", "eo", "oe", "oo"):
        xp, yp = suffix
        p = ((0 if xp == "e" else 1) + (0 if yp == "e" else 1)) % 2
        expected[f"mc_gagg_{suffix}"] = {
            "material": "GAGG", "x": starts[xp], "y": y_starts[yp],
            "z": -15.0 + 2.0 * p,
        }
        expected[f"mc_k9_{suffix}"] = {
            "material": "K9_V1_PROXY", "x": starts[xp], "y": y_starts[yp],
            "z": -13.0 - 2.0 * p,
        }
    return expected


def main():
    with (BASE_DIR / "magiccube_v1_config.json").open(encoding="utf-8") as handle:
        config = json.load(handle)
    lattice = read_csv(BASE_DIR / "magiccube_lattice_map.csv")
    detector = read_csv(BASE_DIR / "detector_map.csv")
    macro = (BASE_DIR / "magiccube_geometry.mac").read_text(encoding="utf-8")
    generator_source = (BASE_DIR / "generate_magiccube_geometry.py").read_text(encoding="utf-8")

    # A. Total counts.
    check(len(lattice) == 4096, "lattice rows must be 4096")
    material_counts = Counter(row["material_concept"] for row in lattice)
    check(material_counts == Counter({"GAGG": 2048, "K9": 2048}), "material totals")
    check(len(detector) == 2048, "detector rows must be 2048")

    # B. Index ranges and uniqueness.
    for key in ("ix", "iy", "k"):
        values = {integer(row, key) for row in lattice}
        check(values == set(range(16)), f"{key} range")
    lattice_ids = [integer(row, "lattice_linear_index") for row in lattice]
    check(len(set(lattice_ids)) == 4096 and min(lattice_ids) == 0 and max(lattice_ids) == 4095,
          "lattice IDs")
    detector_ids = [integer(row, "detector_id") for row in detector]
    check(len(set(detector_ids)) == 2048 and min(detector_ids) == 0 and max(detector_ids) == 2047,
          "detector IDs")

    # C. Material parity and material names.
    for row in lattice:
        ix, iy, k = integer(row, "ix"), integer(row, "iy"), integer(row, "k")
        parity = (ix + iy + k) % 2
        check(integer(row, "parity_3d") == parity, "3-D parity")
        expected_material = "GAGG" if parity == 0 else "K9"
        check(row["material_concept"] == expected_material, "checkerboard material")
        expected_gate = "GAGG" if parity == 0 else "K9_V1_PROXY"
        check(row["gate_material_name"] == expected_gate, "GATE material name")
        if expected_material == "K9":
            check(row["detector_id"] == "" and row["d"] == "", "K9 must not have detector ID/d")

    # D/E. Per-layer and per-bar counts.
    for k in range(16):
        layer = [row for row in lattice if integer(row, "k") == k]
        counts = Counter(row["material_concept"] for row in layer)
        check(counts == Counter({"GAGG": 128, "K9": 128}), f"layer {k} counts")
    bars = defaultdict(list)
    for row in lattice:
        bars[(integer(row, "ix"), integer(row, "iy"))].append(row)
    check(len(bars) == 256, "bar count")
    for bar, rows in bars.items():
        counts = Counter(row["material_concept"] for row in rows)
        check(len(rows) == 16 and counts == Counter({"GAGG": 8, "K9": 8}), f"bar {bar} counts")

    # F/G. GAGG depth relation and canonical detector ID.
    for row in detector:
        ix, iy, d = integer(row, "ix"), integer(row, "iy"), integer(row, "d")
        k = integer(row, "physical_layer_k")
        check(k == 2 * d + ((ix + iy) % 2), "GAGG physical depth relation")
        check((ix + iy + k) % 2 == 0, "detector row is GAGG parity")
        check(integer(row, "detector_id") == d * 256 + iy * 16 + ix, "detector ID formula")
        check(row["gate_material_name"] == "GAGG", "detector map material")

    # H. Detector map is exactly the GAGG subset.
    lattice_gagg = {
        (integer(row, "ix"), integer(row, "iy"), integer(row, "k")): row
        for row in lattice if row["material_concept"] == "GAGG"
    }
    detector_keys = {
        (integer(row, "ix"), integer(row, "iy"), integer(row, "physical_layer_k")): row
        for row in detector
    }
    check(set(lattice_gagg) == set(detector_keys), "detector map GAGG subset")
    for key, drow in detector_keys.items():
        lrow = lattice_gagg[key]
        for field in ("detector_id", "ix", "iy", "x_mm", "y_mm", "z_mm",
                      "lattice_linear_index", "gate_family_name"):
            lattice_value = lrow[field]
            detector_value = drow["physical_layer_k"] if field == "k" else drow[field]
            check(lattice_value == detector_value, f"detector/lattice field {field} at {key}")

    # I/J. Coordinates and mother containment.
    x_values = {number(row, "x_mm") for row in lattice}
    y_values = {number(row, "y_mm") for row in lattice}
    z_values = {number(row, "z_mm") for row in lattice}
    check(min(x_values) == -31.5 and max(x_values) == 31.5, "x center range")
    check(min(y_values) == -31.5 and max(y_values) == 31.5, "y center range")
    check(min(z_values) == -15.0 and max(z_values) == 15.0, "z center range")
    for row in lattice:
        ix, iy, k = integer(row, "ix"), integer(row, "iy"), integer(row, "k")
        close(number(row, "x_mm"), (ix - 7.5) * 4.2, "x formula")
        close(number(row, "y_mm"), (iy - 7.5) * 4.2, "y formula")
        close(number(row, "z_mm"), (k - 7.5) * 2.0, "z formula")
        x, y, z = number(row, "x_mm"), number(row, "y_mm"), number(row, "z_mm")
        check(x - 1.0 >= -33.6 and x + 1.0 <= 33.6, "x mother containment")
        check(y - 1.0 >= -33.6 and y + 1.0 <= 33.6, "y mother containment")
        check(z - 1.0 >= -16.0 and z + 1.0 <= 16.0, "z mother containment")
    check(min(x_values) - 1.0 == -32.5 and max(x_values) + 1.0 == 32.5, "lateral occupied bounds")
    check(min(y_values) - 1.0 == -32.5 and max(y_values) + 1.0 == 32.5, "lateral occupied bounds y")
    check(min(z_values) - 1.0 == -16.0 and max(z_values) + 1.0 == 16.0, "depth occupied bounds")

    # K/L. Gaps, touching, and duplicates.
    check(len({(number(row, "x_mm"), number(row, "y_mm"), number(row, "z_mm")) for row in lattice}) == 4096,
          "duplicate material centers")
    check(len({(integer(row, "ix"), integer(row, "iy"), integer(row, "k")) for row in lattice}) == 4096,
          "duplicate lattice coordinates")
    for values, label in ((sorted({number(row, "x_mm") for row in lattice}), "x centers"),
                          (sorted({number(row, "y_mm") for row in lattice}), "y centers")):
        check(all(math.isclose(b - a, 4.2, abs_tol=1e-9) for a, b in zip(values, values[1:])),
              f"{label} pitch")
    for (ix, iy), rows in bars.items():
        depths = sorted(number(row, "z_mm") for row in rows)
        check(all(math.isclose(b - a, 2.0, abs_tol=1e-9) for a, b in zip(depths, depths[1:])),
              f"depth spacing at bar {(ix, iy)}")
    check(math.isclose(4.2 - 2.0, 2.2, abs_tol=1e-9), "lateral surface gap")
    check(math.isclose(2.0 - 2.0, 0.0, abs_tol=1e-9), "depth faces touch without overlap")

    # M. Family membership and material roles.
    family_rows = defaultdict(list)
    for row in lattice:
        family_rows[row["gate_family_name"]].append(row)
    check(set(family_rows) == set(FAMILY_NAMES), "exact family names")
    for name in FAMILY_NAMES:
        check(len(family_rows[name]) == 512, f"family {name} count")
        expected_material = "GAGG" if name.startswith("mc_gagg_") else "K9"
        check({row["material_concept"] for row in family_rows[name]} == {expected_material},
              f"family {name} material")

    # N/O. Conceptual local indices and exact family start/repeat geometry.
    expected_families = family_expected(config)
    for name, rows in family_rows.items():
        local = [integer(row, "family_local_index_conceptual") for row in rows]
        check(set(local) == set(range(512)), f"family {name} local index")
        for row in rows:
            ix, iy, k = integer(row, "ix"), integer(row, "iy"), integer(row, "k")
            check(integer(row, "family_rx") == ix // 2, f"{name} family_rx")
            check(integer(row, "family_ry") == iy // 2, f"{name} family_ry")
            check(integer(row, "family_rz") == k // 2, f"{name} family_rz")
            expected_local = (k // 2) * 64 + (iy // 2) * 8 + ix // 2
            check(integer(row, "family_local_index_conceptual") == expected_local,
                  f"{name} family local formula")
        expected = expected_families[name]
        xs = sorted({number(row, "x_mm") for row in rows})
        ys = sorted({number(row, "y_mm") for row in rows})
        zs = sorted({number(row, "z_mm") for row in rows})
        check(len(xs) == 8 and len(ys) == 8 and len(zs) == 8, f"{name} repeat cardinality")
        check(all(math.isclose(b - a, 8.4, abs_tol=1e-9) for a, b in zip(xs, xs[1:])), f"{name} x repeat")
        check(all(math.isclose(b - a, 8.4, abs_tol=1e-9) for a, b in zip(ys, ys[1:])), f"{name} y repeat")
        check(all(math.isclose(b - a, 4.0, abs_tol=1e-9) for a, b in zip(zs, zs[1:])), f"{name} z repeat")
        close(xs[0], expected["x"], f"{name} x start")
        close(ys[0], expected["y"], f"{name} y start")
        close(zs[0], expected["z"], f"{name} z start")

    # P. Reconstruct the placements encoded by GATE's first-copy cubicArray
    # semantics and compare them independently with every lattice-map row.
    gate_placements = []
    lattice_map_matches = 0
    outside_mother_placements = 0
    for name in FAMILY_NAMES:
        expected = expected_families[name]
        reconstructed = []
        for rz in range(8):
            for ry in range(8):
                for rx in range(8):
                    x = round(expected["x"] + rx * 8.4, 9)
                    y = round(expected["y"] + ry * 8.4, 9)
                    z = round(expected["z"] + rz * 4.0, 9)
                    placement = (name, expected["material"], x, y, z)
                    reconstructed.append(placement)
                    gate_placements.append(placement)
                    if (x - 1.0 < -33.6 - 1e-9 or x + 1.0 > 33.6 + 1e-9
                            or y - 1.0 < -33.6 - 1e-9 or y + 1.0 > 33.6 + 1e-9
                            or z - 1.0 < -16.0 - 1e-9 or z + 1.0 > 16.0 + 1e-9):
                        outside_mother_placements += 1

        mapped = [
            (
                row["gate_family_name"],
                row["gate_material_name"],
                round(number(row, "x_mm"), 9),
                round(number(row, "y_mm"), 9),
                round(number(row, "z_mm"), 9),
            )
            for row in family_rows[name]
        ]
        check(len(reconstructed) == 512, f"{name} reconstructed placement count")
        check(len(set(reconstructed)) == 512, f"{name} reconstructed placements unique")
        check(len(mapped) == 512 and len(set(mapped)) == 512,
              f"{name} lattice-map placements unique")
        check(set(reconstructed) == set(mapped),
              f"{name} first-copy cubicArray placements match lattice map")
        lattice_map_matches += len(set(reconstructed) & set(mapped))

    duplicate_gate_placements = len(gate_placements) - len(
        {(x, y, z) for _, _, x, y, z in gate_placements}
    )
    check(len(gate_placements) == 4096, "reconstructed GATE placement count")
    check(lattice_map_matches == 4096, "reconstructed GATE placements match lattice map")
    check(duplicate_gate_placements == 0, "duplicate reconstructed GATE placements")
    check(outside_mother_placements == 0, "reconstructed GATE placement outside mother")
    gate_x = [placement[2] for placement in gate_placements]
    gate_y = [placement[3] for placement in gate_placements]
    gate_z = [placement[4] for placement in gate_placements]
    check((min(gate_x), max(gate_x)) == (-31.5, 31.5), "reconstructed x center range")
    check((min(gate_y), max(gate_y)) == (-31.5, 31.5), "reconstructed y center range")
    check((min(gate_z), max(gate_z)) == (-15.0, 15.0), "reconstructed z center range")
    check((min(gate_x) - 1.0, max(gate_x) + 1.0) == (-32.5, 32.5),
          "reconstructed x material bounds")
    check((min(gate_y) - 1.0, max(gate_y) + 1.0) == (-32.5, 32.5),
          "reconstructed y material bounds")
    check((min(gate_z) - 1.0, max(gate_z) + 1.0) == (-16.0, 16.0),
          "reconstructed z material bounds")

    # Q/R. Exact GATE repeater encoding and forbidden legacy content.
    check("magicCubeMother" in macro, "mother name in macro")
    for text in ("Air", "GAGG", "K9_V1_PROXY"):
        check(text in macro, f"macro material {text}")
    check("/gate/magicCubeMother/daughters/insert box" in macro, "mother box insertion")
    for value in ("67.2", "32.0"):
        check(f"{value} mm" in macro, f"mother dimension {value}")
    for name in FAMILY_NAMES:
        expected = expected_families[name]
        check(f"/gate/magicCubeMother/daughters/name {name}" in macro, f"macro family {name}")
        check(f"/gate/{name}/geometry/setXLength 2.0 mm" in macro, f"{name} x length")
        check(f"/gate/{name}/geometry/setYLength 2.0 mm" in macro, f"{name} y length")
        check(f"/gate/{name}/geometry/setZLength 2.0 mm" in macro, f"{name} z length")
        check(f"/gate/{name}/repeaters/insert cubicArray" in macro, f"{name} cubicArray")
        check(f"/gate/{name}/placement/setTranslation {expected['x']} {expected['y']} {expected['z']} mm" in macro,
              f"{name} first-copy translation")
        check(macro.count(f"/gate/{name}/cubicArray/autoCenter false") == 1,
              f"{name} explicit no-autocenter")
        for axis in "XYZ":
            check(f"/gate/{name}/cubicArray/setRepeatNumber{axis} 8" in macro,
                  f"{name} repeat number {axis}")
        check(f"/gate/{name}/cubicArray/setRepeatVector 8.4 8.4 4.0 mm" in macro,
              f"{name} repeat vector")
    auto_center_lines = [
        line.strip() for line in macro.splitlines()
        if "/cubicArray/autoCenter" in line and not line.lstrip().startswith("#")
    ]
    check(len(auto_center_lines) == 8, "exactly eight cubicArray autoCenter settings")
    check(all(line.endswith("/autoCenter false") for line in auto_center_lines),
          "all cubicArray autoCenter settings must be false")
    forbidden = ("xlayer1", "xlayer2", "xlayer3", "xlayer4", "xlayer5", "xlayer6",
                 "xlayer7", "xlayer8", "metalplate", "tungsten", "plate.mac", "cylindricalpet")
    lower_macro = macro.lower()
    check(not any(term in lower_macro for term in forbidden), "legacy geometry absent")
    check("attachcrystalsd" not in lower_macro and "digitizer" not in lower_macro,
          "runtime detector configuration absent")

    # S. Volume sanity.
    segment_volume = 2.0 * 2.0 * 2.0
    mother_volume = 67.2 * 67.2 * 32.0
    close(segment_volume, 8.0, "segment volume")
    close(2048 * segment_volume, 16384.0, "GAGG volume")
    close(2048 * segment_volume, 16384.0, "K9 volume")
    close(4096 * segment_volume, 32768.0, "explicit material volume")
    close(mother_volume, 144506.88, "mother volume")
    close(mother_volume - 4096 * segment_volume, 111738.88, "nominal Air volume")

    # T. Material configuration contract.
    materials = config["materials"]
    check(materials["gagg"]["gate_material_name"] == "GAGG", "config GAGG mapping")
    check(materials["k9"]["gate_material_name"] == "K9_V1_PROXY", "config K9 mapping")
    check(materials["air"]["gate_material_name"] == "Air", "config Air mapping")

    # U. Determinism is statically documented by source structure; no rerun here.
    check("for k in range" in generator_source and "for iy in range" in generator_source
          and "for ix in range" in generator_source, "explicit deterministic iteration")
    check("sorted(" in generator_source and "lineterminator=\"\\n\"" in generator_source,
          "explicit deterministic sorting/output")
    check("datetime" not in generator_source and "uuid" not in generator_source
          and "random" not in generator_source, "no timestamp/UUID/random generation")

    print("Magic-Cube static geometry validation: PASS")
    print("\nlattice positions: 4096\nGAGG: 2048\nK9: 2048\nbars: 256\nphysical layers: 16")
    print("\nGAGG/layer: 128\nK9/layer: 128\n\nGAGG/bar: 8\nK9/bar: 8")
    print("\ndetector IDs: 2048 unique, 0..2047\nlattice IDs: 4096 unique, 0..4095")
    print("\nfamilies: 8\ncopies/family: 512")
    print("\ncubicArray autoCenter disabled: 8/8")
    print(f"reconstructed GATE placements: {len(gate_placements)}")
    print(f"lattice-map matches: {lattice_map_matches}")
    print(f"duplicate placements: {duplicate_gate_placements}")
    print(f"outside-mother placements: {outside_mother_placements}")
    print("\nx center range: -31.5..31.5 mm\ny center range: -31.5..31.5 mm\nz center range: -15..15 mm")
    print("\nouter lateral material bounds: -32.5..32.5 mm\ndepth material bounds: -16..16 mm")
    print("\nlateral gap: 2.2 mm\ndepth overlap: none; adjacent segments touch")
    print("\ngenerated macro contract: PASS\nmaterial contract: PASS")


if __name__ == "__main__":
    main()
