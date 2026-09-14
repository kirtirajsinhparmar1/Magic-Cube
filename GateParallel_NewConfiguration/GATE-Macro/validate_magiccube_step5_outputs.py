#!/usr/bin/env python3
"""Validate user-produced bounded Step-5 ROOT output.

This script is intentionally runtime-only: it reads ROOT files and logs made
by the user's manual GATE run.  It never launches GATE or a scheduler.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


GAGG_FAMILIES = (
    "mc_gagg_ee",
    "mc_gagg_eo",
    "mc_gagg_oe",
    "mc_gagg_oo",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a manually generated Magic-Cube Step-5 ROOT output."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--gate-exit-code",
        type=int,
        default=None,
        help="Gate exit code; if omitted, read magiccube_step5_gate.exit_code.",
    )
    return parser.parse_args()


def clean_key(key: object) -> str:
    return str(key).split(";", 1)[0]


def read_gate_exit_code(output_dir: Path, supplied: int | None) -> int | None:
    if supplied is not None:
        return supplied
    path = output_dir / "magiccube_step5_gate.exit_code"
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def log_error_lines(output_dir: Path) -> list[str]:
    pattern = re.compile(
        r"(?i)(?:G4Exception.*fatal|fatal\s+(?:exception|error)|"
        r"unhandled\s+exception|unknown\s+command|illegal\s+command|"
        r"geometry\s+(?:exception|error)|digitizer.*(?:fatal|exception|error))"
    )
    matches: list[str] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".log", ".out", ".err"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        matches.extend(f"{path.name}: {line.strip()}" for line in lines if pattern.search(line))
    return matches


def inspect_root(path: Path) -> dict[str, object]:
    import uproot  # Imported only when the user asks for ROOT validation.

    records: list[dict[str, object]] = []
    collections: set[str] = set()
    family_tokens: set[str] = set()
    hits_entries = 0
    singles_entries = 0
    with uproot.open(path) as root_file:
        keys = list(root_file.keys(recursive=True))
        for raw_key in keys:
            key = clean_key(raw_key)
            try:
                obj = root_file[raw_key]
                entries = int(obj.num_entries)
                branch_names = [clean_key(name) for name in obj.keys()]
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
            context = " ".join([key, *branch_names])
            lowered = context.lower()
            if entries <= 0:
                continue
            has_edep = bool(re.search(r"(?:^|[^a-z])edep(?:$|[^a-z])", lowered))
            has_hits_token = bool(re.search(r"(?:^|[^a-z])hits?(?:$|[^a-z])", lowered))
            has_singles_token = bool(
                re.search(r"(?:^|[^a-z])singles?(?:$|[^a-z])", lowered)
            )
            has_energy = "energy" in lowered
            has_event = "eventid" in lowered or "event_id" in lowered
            is_hits = has_edep or has_hits_token
            is_singles = has_singles_token or (has_energy and has_event and not has_edep)
            if is_hits:
                hits_entries += entries
            if is_singles:
                singles_entries += entries
            for collection in ("Hits", "Singles"):
                if re.search(rf"(?:^|[^a-z]){collection.lower()}(?:$|[^a-z])", lowered):
                    collections.add(collection)
            for family in GAGG_FAMILIES:
                if family in lowered:
                    family_tokens.add(family)
            records.append(
                {
                    "key": key,
                    "entries": entries,
                    "branches": branch_names,
                    "hits_like": is_hits,
                    "singles_like": is_singles,
                }
            )
    return {
        "records": records,
        "collections": sorted(collections),
        "family_tokens": sorted(family_tokens),
        "hits_entries": hits_entries,
        "singles_entries": singles_entries,
    }


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    failures: list[str] = []

    def check(condition: bool, label: str, detail: str = "") -> None:
        if condition:
            print(f"PASS: {label}")
        else:
            message = f"FAIL: {label}"
            if detail:
                message += f" — {detail}"
            print(message)
            failures.append(message)

    check(output_dir.is_dir(), "Step-5 runtime output directory exists", str(output_dir))
    if not output_dir.is_dir():
        print("RUNTIME VALIDATION: FAIL")
        return 1

    gate_exit_code = read_gate_exit_code(output_dir, args.gate_exit_code)
    check(gate_exit_code is not None, "Gate exit code is recorded")
    check(gate_exit_code == 0, "Gate exit code is zero", f"exit_code={gate_exit_code}")

    errors = log_error_lines(output_dir)
    check(not errors, "logs contain no fatal geometry or digitizer exception", "; ".join(errors))

    root_files = sorted(output_dir.glob("*.root"))
    check(bool(root_files), "at least one ROOT output exists")

    total_hits = 0
    total_singles = 0
    all_records: list[dict[str, object]] = []
    all_collections: set[str] = set()
    all_families: set[str] = set()
    readable_files = 0
    import_error: str | None = None
    if root_files:
        try:
            for root_path in root_files:
                report = inspect_root(root_path)
                readable_files += 1
                total_hits += int(report["hits_entries"])
                total_singles += int(report["singles_entries"])
                all_records.extend(
                    {"file": root_path.name, **record}
                    for record in report["records"]  # type: ignore[union-attr]
                )
                all_collections.update(report["collections"])  # type: ignore[arg-type]
                all_families.update(report["family_tokens"])  # type: ignore[arg-type]
        except Exception as exc:  # ROOT parser errors must become a validation failure.
            import_error = f"{type(exc).__name__}: {exc}"
    check(
        import_error is None and readable_files == len(root_files),
        "all ROOT outputs are readable",
        import_error or f"readable={readable_files}/{len(root_files)}",
    )
    check(total_hits > 0, "at least one non-empty Hits output exists", f"entries={total_hits}")
    check(
        total_singles > 0,
        "at least one non-empty Singles output exists",
        f"entries={total_singles}",
    )
    check(
        "Singles" in all_collections or total_singles > 0,
        "digitized Singles collection/output is present",
        f"collections={sorted(all_collections)}",
    )
    if all_families:
        check(
            all_families == set(GAGG_FAMILIES),
            "all explicitly named GAGG-family outputs are represented",
            f"families={sorted(all_families)}",
        )
    else:
        print(
            "INFO: ROOT output has no explicit family-name token; the original "
            "common Singles collection convention is accepted."
        )
    print(f"ROOT files: {[path.name for path in root_files]}")
    print(f"Collections detected: {sorted(all_collections)}")
    print(f"Hits entries: {total_hits}")
    print(f"Singles entries: {total_singles}")
    for record in all_records[:40]:
        print(
            f"Tree {record['file']}:{record['key']} entries={record['entries']} "
            f"hits_like={record['hits_like']} singles_like={record['singles_like']} "
            f"branches={record['branches']}"
        )

    if failures:
        print(f"RUNTIME VALIDATION: FAIL ({len(failures)} failed checks)")
        return 1
    print("RUNTIME VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
