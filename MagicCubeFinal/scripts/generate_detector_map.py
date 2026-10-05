#!/usr/bin/env python3
"""Generate the canonical GAGG channel map without running GATE."""
import argparse
import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def validate_config(config):
    """Reject drift from the frozen geometry represented by the copied macros."""
    expected = {
        "nx": 16, "ny": 16, "nz": 16,
        "pitch_x_mm": 4.2, "pitch_y_mm": 4.2, "pitch_z_mm": 2.0,
        "segment_size_x_mm": 2.0, "segment_size_y_mm": 2.0, "segment_size_z_mm": 2.0,
    }
    for key, value in expected.items():
        if config["lattice"][key] != value:
            raise ValueError(f"Frozen lattice.{key} must be {value}")
    if config["detector"]["mother_size_mm"] != {"x": 67.2, "y": 67.2, "z": 32.0}:
        raise ValueError("Frozen detector mother dimensions have changed")
    if config["material_pattern"] != {"rule": "(ix + iy + k) % 2", "gagg_when_remainder": 0, "k9_when_remainder": 1}:
        raise ValueError("Frozen material parity rule has changed")
    if config["counts"] != {"total_lattice_positions": 4096, "gagg_elements": 2048, "k9_elements": 2048}:
        raise ValueError("Frozen detector element counts have changed")
    for name, material in (("gagg", "GAGG"), ("k9", "K9_V1_PROXY"), ("air", "Air")):
        if config["materials"][name]["gate_material_name"] != material:
            raise ValueError(f"Frozen material {name} must be {material}")
    if config["indexing"]["detector_id"] != "d * 256 + iy * 16 + ix" or config["indexing"]["physical_layer_k"] != "2 * d + ((ix + iy) % 2)":
        raise ValueError("Frozen detector indexing has changed")


def detector_rows(config):
    validate_config(config)
    lattice = config["lattice"]
    nx, ny, nz = (lattice[key] for key in ("nx", "ny", "nz"))
    if (nx, ny, nz) != (16, 16, 16):
        raise ValueError("Frozen detector indexing requires the 16x16x16 lattice")
    if config["material_pattern"]["gagg_when_remainder"] != 0:
        raise ValueError("Frozen GAGG parity must be even")
    rows = []
    for d in range(nz // 2):
        for iy in range(ny):
            for ix in range(nx):
                k = 2 * d + ((ix + iy) % 2)
                suffix = ("e" if ix % 2 == 0 else "o") + ("e" if iy % 2 == 0 else "o")
                rows.append({
                    "detector_id": d * 256 + iy * 16 + ix,
                    "ix": ix, "iy": iy, "d": d, "physical_layer_k": k, "depth_index": k,
                    "x_mm": round((ix - (nx - 1) / 2) * lattice["pitch_x_mm"], 9),
                    "y_mm": round((iy - (ny - 1) / 2) * lattice["pitch_y_mm"], 9),
                    "z_mm": round((k - (nz - 1) / 2) * lattice["pitch_z_mm"], 9),
                    "lattice_linear_index": k * 256 + iy * 16 + ix,
                    "ix_parity": "even" if ix % 2 == 0 else "odd",
                    "iy_parity": "even" if iy % 2 == 0 else "odd",
                    "gate_family_name": "mc_gagg_" + suffix, "family": "mc_gagg_" + suffix,
                    "gate_material_name": config["materials"]["gagg"]["gate_material_name"],
                    "material": "GAGG", "is_sensitive": True,
                    "family_rx": ix // 2, "family_ry": iy // 2, "family_rz": d,
                    "family_local_index_conceptual": d * 64 + (iy // 2) * 8 + ix // 2,
                })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=BASE / "config/magiccube_config.json")
    parser.add_argument("--output", type=Path, default=BASE / "config/detector_map.csv")
    parser.add_argument("--parquet", type=Path, help="Optional parquet output if pyarrow is installed")
    args = parser.parse_args()
    rows = detector_rows(json.loads(args.config.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} canonical detectors to {args.output}")
    if args.parquet:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            print("Parquet unavailable: optional pyarrow is not installed; CSV remains authoritative")
        else:
            args.parquet.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pylist(rows), args.parquet)


if __name__ == "__main__":
    main()
