#!/usr/bin/env python3
"""Inspect real Step-4 ROOT files and classify Magic-Cube detector identity."""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path
from typing import Any

import uproot


WORKDIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(
    "/vscratch/grp-rutaoyao/Kirtiraj/Magic Cube/runtime_validation/step4"
)
DETECTOR_MAP = WORKDIR / "detector_map.csv"
LATTICE_MAP = WORKDIR / "magiccube_lattice_map.csv"
OBSERVATIONS_CSV = WORKDIR / "magiccube_runtime_id_observations.csv"
IDENTITY_JSON = WORKDIR / "magiccube_runtime_identity.json"

GAGG_FAMILIES = (
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
)
IDENTITY_CLASSES = (
    "ID_ONLY_VALIDATED",
    "ID_PLUS_FAMILY_VALIDATED",
    "POSITION_DERIVED_REQUIRED",
    "UNRESOLVED",
)
POSITION_TOLERANCE_MM = 1.0e-6
CUBE_HALF_SIZE_MM = 1.0
IDENTITY_BRANCH_PATTERN = re.compile(
    r"(?:volumeid|rsectorid|moduleid|submoduleid|crystalid|layerid|"
    r"copy(?:id|no|number)|replica(?:id|no|number))",
    re.IGNORECASE,
)


def load_detector_map() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with DETECTOR_MAP.open(newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            row: dict[str, Any] = dict(raw)
            for key in (
                "detector_id",
                "ix",
                "iy",
                "d",
                "physical_layer_k",
                "family_rx",
                "family_ry",
                "family_rz",
            ):
                row[key] = int(raw[key])
            for key in ("x_mm", "y_mm", "z_mm"):
                row[key] = float(raw[key])
            rows.append(row)
    return rows


def load_lattice_map() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with LATTICE_MAP.open(newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            material = (
                raw.get("conceptual_material")
                or raw.get("material")
                or raw.get("gate_material_name")
                or ""
            )
            rows.append(
                {
                    "x_mm": float(raw["x_mm"]),
                    "y_mm": float(raw["y_mm"]),
                    "z_mm": float(raw["z_mm"]),
                    "material": material,
                }
            )
    return rows


def containing_rows(
    x_mm: float,
    y_mm: float,
    z_mm: float,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    limit = CUBE_HALF_SIZE_MM + POSITION_TOLERANCE_MM
    return [
        row
        for row in rows
        if abs(x_mm - float(row["x_mm"])) <= limit
        and abs(y_mm - float(row["y_mm"])) <= limit
        and abs(z_mm - float(row["z_mm"])) <= limit
    ]


def normalize_branch_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def select_branch(branches: list[str], requested: str) -> str | None:
    target = normalize_branch_name(requested)
    exact = [name for name in branches if normalize_branch_name(name) == target]
    if exact:
        return exact[0]
    suffix = [name for name in branches if normalize_branch_name(name).endswith(target)]
    return suffix[0] if suffix else None


def discover_hit_tree(root_path: Path) -> dict[str, Any]:
    with uproot.open(root_path) as root_file:
        root_keys = [str(key) for key in root_file.keys(recursive=True, cycle=False)]
        trees: list[dict[str, Any]] = []
        candidates: list[tuple[int, dict[str, Any]]] = []
        for key in root_keys:
            try:
                item = root_file[key]
            except Exception:
                continue
            if not hasattr(item, "arrays") or not hasattr(item, "num_entries"):
                continue
            branches = [str(name) for name in item.keys()]
            roles = {
                role: select_branch(branches, role)
                for role in (
                    "runID",
                    "eventID",
                    "sourceID",
                    "sourcePosX",
                    "sourcePosY",
                    "sourcePosZ",
                    "posX",
                    "posY",
                    "posZ",
                    "edep",
                )
            }
            identity_branches = [
                name for name in branches if IDENTITY_BRANCH_PATTERN.search(name)
            ]
            tree_record = {
                "name": key,
                "entries": int(item.num_entries),
                "branches": branches,
                "discovered_fields": roles,
                "runtime_identity_branches": identity_branches,
            }
            trees.append(tree_record)
            required = ("eventID", "posX", "posY", "posZ", "edep")
            if all(roles[name] is not None for name in required):
                score = (100 if "hit" in key.lower() else 0) + int(item.num_entries > 0)
                candidates.append((score, tree_record))

        if not candidates:
            raise RuntimeError(
                f"{root_path} has no tree with eventID, edep, posX, posY, and posZ"
            )
        selected = max(candidates, key=lambda item: item[0])[1]
        return {
            "root_file": str(root_path),
            "root_keys": root_keys,
            "trees": trees,
            "selected_tree": selected["name"],
            "selected_fields": selected["discovered_fields"],
            "runtime_identity_branches": selected["runtime_identity_branches"],
            "required_fields_available": True,
        }


def python_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, tuple):
        return [python_value(item) for item in value]
    if isinstance(value, list):
        return [python_value(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def numeric_identity_components(branch: str, value: Any) -> dict[str, int]:
    components: dict[str, int] = {}

    def visit(label: str, item: Any) -> None:
        item = python_value(item)
        if isinstance(item, list):
            for index, nested in enumerate(item):
                visit(f"{label}[{index}]", nested)
            return
        if isinstance(item, bool):
            components[label] = int(item)
            return
        if isinstance(item, int):
            components[label] = item
            return
        if isinstance(item, float) and math.isfinite(item) and item.is_integer():
            components[label] = int(item)

    visit(branch, value)
    return components


def array_value(arrays: Any, branch: str, index: int) -> Any:
    return arrays[branch][index]


def analyze_root(
    root_path: Path,
    detector_rows: list[dict[str, Any]],
    lattice_rows: list[dict[str, Any]],
    expected_detector_id: int | None,
) -> dict[str, Any]:
    schema = discover_hit_tree(root_path)
    selected_fields = schema["selected_fields"]
    identity_branches = schema["runtime_identity_branches"]
    read_branches = sorted(
        {
            branch
            for branch in list(selected_fields.values()) + list(identity_branches)
            if branch is not None
        }
    )
    with uproot.open(root_path) as root_file:
        tree = root_file[schema["selected_tree"]]
        arrays = tree.arrays(read_branches, library="np")

    edep_branch = selected_fields["edep"]
    assert edep_branch is not None
    raw_entries = len(arrays[edep_branch])
    hits: list[dict[str, Any]] = []
    for index in range(raw_entries):
        edep = float(array_value(arrays, edep_branch, index))
        if not math.isfinite(edep) or edep <= 0.0:
            continue
        x_mm = float(array_value(arrays, selected_fields["posX"], index))
        y_mm = float(array_value(arrays, selected_fields["posY"], index))
        z_mm = float(array_value(arrays, selected_fields["posZ"], index))
        detector_candidates = containing_rows(x_mm, y_mm, z_mm, detector_rows)
        mapping = (
            "unique"
            if len(detector_candidates) == 1
            else "unmapped"
            if len(detector_candidates) == 0
            else "ambiguous"
        )
        detector_id = (
            int(detector_candidates[0]["detector_id"])
            if len(detector_candidates) == 1
            else None
        )
        k9_candidate = False
        if not detector_candidates:
            material_candidates = containing_rows(x_mm, y_mm, z_mm, lattice_rows)
            if len(material_candidates) == 1:
                material = str(material_candidates[0]["material"]).upper()
                k9_candidate = "K9" in material

        identity_components: dict[str, int] = {}
        identity_values: dict[str, Any] = {}
        for branch in identity_branches:
            value = python_value(array_value(arrays, branch, index))
            identity_values[branch] = value
            identity_components.update(numeric_identity_components(branch, value))

        hits.append(
            {
                "event_id": int(
                    array_value(arrays, selected_fields["eventID"], index)
                ),
                "edep": edep,
                "x_mm": x_mm,
                "y_mm": y_mm,
                "z_mm": z_mm,
                "mapping": mapping,
                "detector_id": detector_id,
                "correct": detector_id == expected_detector_id
                if expected_detector_id is not None
                else False,
                "mismatched": detector_id is not None
                and expected_detector_id is not None
                and detector_id != expected_detector_id,
                "k9_candidate": k9_candidate,
                "identity_values": identity_values,
                "identity_components": identity_components,
            }
        )

    return {
        "schema": schema,
        "raw_entries": raw_entries,
        "positive_edep_hits": len(hits),
        "hits": hits,
        "unique": sum(hit["mapping"] == "unique" for hit in hits),
        "unmapped": sum(hit["mapping"] == "unmapped" for hit in hits),
        "ambiguous": sum(hit["mapping"] == "ambiguous" for hit in hits),
        "correct": sum(bool(hit["correct"]) for hit in hits),
        "mismatched": sum(bool(hit["mismatched"]) for hit in hits),
        "k9_sensitive_hits": sum(bool(hit["k9_candidate"]) for hit in hits),
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def geometry_initialization() -> dict[str, Any]:
    exit_path = OUTPUT_DIR / "geometry_check.exit_code"
    if not exit_path.is_file():
        return {"executed": False, "exit_code": None, "passed": False}
    try:
        exit_code = int(exit_path.read_text(encoding="utf-8").strip())
    except ValueError:
        exit_code = None
    return {
        "executed": True,
        "exit_code": exit_code,
        "passed": exit_code == 0,
        "stdout": str(OUTPUT_DIR / "geometry_check.stdout"),
        "stderr": str(OUTPUT_DIR / "geometry_check.stderr"),
    }


def status_root_files(status: dict[str, Any]) -> list[Path]:
    """Return only files recorded by a successful, current Gate invocation."""
    if status.get("exit_code") != 0:
        return []
    root_files = status.get("root_files")
    if not isinstance(root_files, list) or not root_files:
        return []
    paths = [Path(str(item)) for item in root_files]
    if len(paths) != len(set(paths)) or not all(path.is_file() for path in paths):
        return []
    return paths


def expected_probe_root_file(
    status: dict[str, Any], expected_family: str
) -> Path | None:
    """Select the expected GAGG collection, or a single consolidated ROOT file."""
    paths = status_root_files(status)
    if len(paths) == 1:
        return paths[0]
    suffix = f".hits_{expected_family}.root"
    matches = [path for path in paths if path.name.endswith(suffix)]
    return matches[0] if len(matches) == 1 else None


def stable_component_values(
    hits: list[dict[str, Any]],
) -> dict[str, int]:
    if not hits:
        return {}
    component_names = set.intersection(
        *(set(hit["identity_components"]) for hit in hits)
    )
    stable: dict[str, int] = {}
    for name in component_names:
        values = {int(hit["identity_components"][name]) for hit in hits}
        if len(values) == 1:
            stable[name] = values.pop()
    return stable


def classify_runtime_identity(
    expected_by_probe: dict[int, dict[str, Any]],
    samples: dict[str, dict[int, int]],
    position_mapping_validated: bool,
) -> tuple[str, dict[str, Any]]:
    probe_ids = set(expected_by_probe)
    direct_candidates: list[str] = []
    family_candidates: list[dict[str, Any]] = []
    for component, values_by_probe in samples.items():
        if set(values_by_probe) != probe_ids:
            continue
        if all(
            values_by_probe[probe_id]
            == int(expected_by_probe[probe_id]["detector_id"])
            for probe_id in probe_ids
        ):
            direct_candidates.append(component)

        for order in permutations(("rx", "ry", "rz")):
            matches = True
            for probe_id in probe_ids:
                expected = expected_by_probe[probe_id]
                coordinate = {
                    "rx": int(expected["family_rx"]),
                    "ry": int(expected["family_ry"]),
                    "rz": int(expected["family_rz"]),
                }
                flattened = (
                    coordinate[order[0]] * 64
                    + coordinate[order[1]] * 8
                    + coordinate[order[2]]
                )
                if values_by_probe[probe_id] != flattened:
                    matches = False
                    break
            if matches:
                family_candidates.append(
                    {"component": component, "flattening_order": list(order)}
                )

    evidence = {
        "direct_detector_id_components": sorted(direct_candidates),
        "family_local_components": sorted(
            family_candidates,
            key=lambda item: (item["component"], item["flattening_order"]),
        ),
        "tested_flattening_permutations": 6,
    }
    if direct_candidates:
        return "ID_ONLY_VALIDATED", evidence
    if family_candidates:
        return "ID_PLUS_FAMILY_VALIDATED", evidence
    if position_mapping_validated:
        return "POSITION_DERIVED_REQUIRED", evidence
    return "UNRESOLVED", evidence


def main() -> int:
    detector_rows = load_detector_map()
    lattice_rows = load_lattice_map()
    geometry = geometry_initialization()
    probe_status_paths = sorted(OUTPUT_DIR.glob("probe_[0-9][0-9].status.json"))
    smoke_status_paths = sorted(OUTPUT_DIR.glob("smoke_140kev.status.json"))

    observations: list[dict[str, Any]] = []
    schemas: list[dict[str, Any]] = []
    probe_errors: list[str] = []
    expected_by_probe: dict[int, dict[str, Any]] = {}
    component_samples: dict[str, dict[int, int]] = defaultdict(dict)
    family_success = {family: False for family in GAGG_FAMILIES}
    probe_totals = defaultdict(int)
    successful_probes = 0
    analyzed_probes = 0
    probe_root_files = 0

    for status_path in probe_status_paths:
        status = read_json(status_path)
        expected = status.get("expected")
        if not isinstance(expected, dict):
            probe_errors.append(f"{status_path.name}: missing expected probe metadata")
            continue
        probe_id = int(expected["probe_index"])
        expected_by_probe[probe_id] = expected
        root_path = expected_probe_root_file(
            status, str(expected["gate_family_name"])
        )
        if root_path is None:
            probe_errors.append(
                f"{status_path.name}: no successful current ROOT output "
                "for the expected GAGG collection"
            )
            continue
        probe_root_files += 1
        try:
            analysis = analyze_root(
                root_path,
                detector_rows,
                lattice_rows,
                int(expected["detector_id"]),
            )
        except Exception as exc:
            probe_errors.append(f"{status_path.name}: {exc}")
            continue
        analyzed_probes += 1
        schemas.append(analysis["schema"])
        for key in (
            "positive_edep_hits",
            "unique",
            "unmapped",
            "ambiguous",
            "correct",
            "mismatched",
            "k9_sensitive_hits",
        ):
            probe_totals[key] += int(analysis[key])

        correct_hits = [hit for hit in analysis["hits"] if hit["correct"]]
        if correct_hits:
            successful_probes += 1
            family_success[str(expected["gate_family_name"])] = True
        for component, value in stable_component_values(correct_hits).items():
            component_samples[component][probe_id] = value

        for hit in analysis["hits"]:
            detector_id = hit["detector_id"]
            observations.append(
                {
                    "probe_index": probe_id,
                    "run_name": status["run_name"],
                    "gate_family_name": expected["gate_family_name"],
                    "expected_detector_id": expected["detector_id"],
                    "event_id": hit["event_id"],
                    "edep": hit["edep"],
                    "pos_x_mm": hit["x_mm"],
                    "pos_y_mm": hit["y_mm"],
                    "pos_z_mm": hit["z_mm"],
                    "position_mapping": hit["mapping"],
                    "mapped_detector_id": "" if detector_id is None else detector_id,
                    "classification": (
                        "mismatched"
                        if hit["mismatched"]
                        else "uniquely mapped"
                        if hit["mapping"] == "unique"
                        else hit["mapping"]
                    ),
                    "runtime_identity_values": json.dumps(
                        hit["identity_values"], sort_keys=True
                    ),
                    "runtime_identity_components": json.dumps(
                        hit["identity_components"], sort_keys=True
                    ),
                }
            )

    invalid_detector_ids = sum(
        1
        for row in observations
        if row["mapped_detector_id"] != ""
        and not 0 <= int(row["mapped_detector_id"]) <= 2047
    )
    position_mapping_validated = (
        len(probe_status_paths) == 32
        and analyzed_probes == 32
        and successful_probes == 32
        and probe_totals["positive_edep_hits"] > 0
        and probe_totals["unmapped"] == 0
        and probe_totals["ambiguous"] == 0
        and invalid_detector_ids == 0
    )
    identity_classification, identity_evidence = classify_runtime_identity(
        expected_by_probe,
        component_samples,
        position_mapping_validated,
    )
    if identity_classification not in IDENTITY_CLASSES:
        raise AssertionError(identity_classification)

    smoke_errors: list[str] = []
    smoke_hits = 0
    smoke_k9_hits = 0
    smoke_root_files = 0
    smoke_source: dict[str, Any] | None = None
    for status_path in smoke_status_paths:
        status = read_json(status_path)
        smoke_source = status.get("source")
        root_paths = status_root_files(status)
        if not root_paths:
            smoke_errors.append(f"{status_path.name}: no successful current ROOT output")
            continue
        status_analyses: list[dict[str, Any]] = []
        for root_path in root_paths:
            try:
                status_analyses.append(
                    analyze_root(root_path, detector_rows, lattice_rows, None)
                )
            except Exception as exc:
                smoke_errors.append(f"{status_path.name} ({root_path.name}): {exc}")
        if len(status_analyses) != len(root_paths):
            continue
        smoke_root_files += len(status_analyses)
        for analysis in status_analyses:
            schemas.append(analysis["schema"])
            smoke_hits += int(analysis["positive_edep_hits"])
            smoke_k9_hits += int(analysis["k9_sensitive_hits"])

    required_fields_available = bool(schemas) and all(
        bool(schema["required_fields_available"]) for schema in schemas
    )
    k9_sensitive_hits = probe_totals["k9_sensitive_hits"] + smoke_k9_hits
    smoke_executed = (
        len(smoke_status_paths) == 1
        and smoke_root_files >= 1
        and not smoke_errors
    )
    complete = (
        geometry["passed"]
        and len(probe_status_paths) == 32
        and analyzed_probes == 32
        and successful_probes == 32
        and required_fields_available
        and identity_classification != "UNRESOLVED"
        and k9_sensitive_hits == 0
        and smoke_executed
        and smoke_hits > 0
    )

    report = {
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "geometry_initialization": geometry,
        "root_schema_discovery": {
            "required_fields": ["eventID", "edep", "posX", "posY", "posZ"],
            "required_fields_available": required_fields_available,
            "files": schemas,
        },
        "probe_summary": {
            "status_records": len(probe_status_paths),
            "root_files_analyzed": probe_root_files,
            "analyzed_probes": analyzed_probes,
            "successful_probes": successful_probes,
            "total_hits": probe_totals["positive_edep_hits"],
            "uniquely_mapped_hits": probe_totals["unique"],
            "unmapped_hits": probe_totals["unmapped"],
            "ambiguous_hits": probe_totals["ambiguous"],
            "correct_expected_detector_hits": probe_totals["correct"],
            "mismatched_hits": probe_totals["mismatched"],
            "invalid_detector_ids": invalid_detector_ids,
            "families_with_useful_hits": family_success,
            "errors": probe_errors,
        },
        "sensitive_detector": {
            "attached_gagg_families": list(GAGG_FAMILIES),
            "k9_sensitive_hits": k9_sensitive_hits,
            "k9_sensitive": k9_sensitive_hits > 0,
        },
        "identity": {
            "classification": identity_classification,
            "position_mapping_validated": position_mapping_validated,
            "evidence": identity_evidence,
        },
        "smoke_140kev": {
            "status_records": len(smoke_status_paths),
            "root_files_analyzed": smoke_root_files,
            "executed": smoke_executed,
            "source": smoke_source,
            "total_hits": smoke_hits,
            "k9_sensitive_hits": smoke_k9_hits,
            "errors": smoke_errors,
        },
    }

    fieldnames = [
        "probe_index",
        "run_name",
        "gate_family_name",
        "expected_detector_id",
        "event_id",
        "edep",
        "pos_x_mm",
        "pos_y_mm",
        "pos_z_mm",
        "position_mapping",
        "mapped_detector_id",
        "classification",
        "runtime_identity_values",
        "runtime_identity_components",
    ]
    with OBSERVATIONS_CSV.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(observations)
    IDENTITY_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Magic-Cube runtime identity classification: {identity_classification}")
    print(f"Runtime identity report: {IDENTITY_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
