#!/usr/bin/env python3
"""Print the compact report from already-generated OneCube products."""

import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "onecube_config.json"
RESULTS = PROJECT_ROOT / "results"


def main() -> int:
    with CONFIG_PATH.open(encoding="utf-8") as stream:
        config = json.load(stream)
    with (RESULTS / "validation" / "root_summary.json").open(encoding="utf-8") as stream:
        root_summary = json.load(stream)
    with (RESULTS / "validation" / "final_validation.json").open(encoding="utf-8") as stream:
        validation = json.load(stream)
    ppdf = pd.read_parquet(RESULTS / "ppdf" / "ppdf.parquet").iloc[0]
    matrix = pd.read_parquet(RESULTS / "system_matrix" / "system_matrix.parquet").iloc[0]

    detector = config["detector"]
    source = config["source"]
    print("OneCube detector:")
    print(f"    {detector['size_x_mm']:g} x {detector['size_y_mm']:g} x {detector['size_z_mm']:g} mm {detector['material']}")
    print(f"    detector ID {detector['detector_id']}")
    print("Source:")
    print(f"    {source['energy_keV']:g} keV")
    print(f"    position ({source['x_mm']:g},{source['y_mm']:g},{source['z_mm']:g}) mm")
    print(f"    {source['surface_distance_mm']:g}-mm surface distance")
    print(f"    {source['activity_Bq'] / 1.0e6:g} MBq")
    print(f"    {config['acquisition']['duration_s']:g} s")
    print("Runtime:")
    print(f"    Gate exit code: {(PROJECT_ROOT / 'runtime' / 'sim' / 'gate_exit_code.txt').read_text(encoding='utf-8').strip()}")
    print("Hits:")
    print(f"    count {root_summary['hits_count']}")
    print("Singles:")
    print(f"    count {root_summary['singles_count']}")
    print("PPDF:")
    print(f"    {float(ppdf['ppdf']):g}")
    print("Matrix:")
    print("    shape 1x1")
    print(f"    raw count {int(matrix['raw_singles_count'])}")
    print(f"    cps/MBq {float(matrix['response_cps_per_MBq']):g}")
    print("Final:")
    print(f"    {validation['classification']}")
    return 0 if validation.get("classification") == "ONECUBE_END_TO_END_PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - report missing upstream products
        print(f"Final summary failed: {error}", file=sys.stderr)
        sys.exit(1)
