#!/usr/bin/env python3
"""Reduce independent Gate phantom acquisitions and run separate MLEM analyses."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from onecube_imaging.io import file_sha256, load_config, read_csv, root_tree_entries, save_npy, write_csv, write_runtime_json
from reconstruction.forward_project import forward_project
from reconstruction.metrics import reconstruction_metrics
from reconstruction.mlem import mlem
from visualization.imaging_plots import plot_reconstruction_results


def reconstruct() -> dict:
    config = load_config(PROJECT_ROOT)
    manifest = read_csv(PROJECT_ROOT / "runtime/manifests/phantom_acquisition_manifest.csv")
    measurements = []
    for row in manifest:
        task_id = int(row["task_id"])
        completion_path = PROJECT_ROOT / f"runtime/phantom/completions/task_{task_id:03d}.json"
        singles_path = PROJECT_ROOT / row["singles_root_path"]
        hits_path = PROJECT_ROOT / row["hits_root_path"]
        if not completion_path.is_file():
            raise RuntimeError(f"Phantom task {task_id} has no completion record")
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        if completion.get("status") != "completed":
            raise RuntimeError(f"Phantom task {task_id} status is {completion.get('status')}")
        if completion.get("singles_sha256") != file_sha256(singles_path):
            raise RuntimeError(f"Phantom task {task_id} Singles ROOT hash changed")
        if completion.get("hits_sha256") != file_sha256(hits_path):
            raise RuntimeError(f"Phantom task {task_id} Hits ROOT hash changed")
        singles_count = root_tree_entries(singles_path)
        hits_count = root_tree_entries(hits_path)
        if singles_count != int(completion["singles_entries"]) or hits_count != int(completion["hits_entries"]):
            raise RuntimeError(f"Phantom task {task_id} ROOT counts changed after completion")
        measurements.append({
            "row_id": int(row["row_id"]),
            "pose_id": int(row["pose_id"]),
            "task_id": task_id,
            "raw_singles_count": singles_count,
            "raw_hits_count": hits_count,
            "seed": int(row["seed"]),
            "completion_path": str(completion_path),
            "singles_sha256": file_sha256(singles_path),
        })
    measurements.sort(key=lambda row: row["row_id"])
    y_gate = np.asarray([row["raw_singles_count"] for row in measurements], dtype=np.float64)
    if y_gate.size != len(manifest):
        raise RuntimeError("Measured phantom vector does not have one entry per physical pose")

    operator = np.load(PROJECT_ROOT / "results/system_matrix/count_operator_counts_per_bq.npy")
    truth = np.load(PROJECT_ROOT / "results/phantom/phantom_activity_bq.npy")
    phantom_image = np.load(PROJECT_ROOT / "results/phantom/phantom_image_bq.npy")
    if operator.shape != (len(manifest), truth.size):
        raise RuntimeError(f"Count operator {operator.shape} does not match measured rows and phantom voxels")
    expected, poisson = forward_project(
        operator, truth, int(config["reconstruction"]["poisson_seed"])
    )
    reconstruction_config = config["reconstruction"]
    observable = (operator.T @ np.ones(operator.shape[0])) > 0
    initial = np.zeros(truth.size, dtype=np.float64)
    initial[observable] = float(truth.sum()) / max(int(observable.sum()), 1)
    synthetic_estimate, synthetic_history = mlem(
        operator,
        poisson,
        int(reconstruction_config["iterations"]),
        float(reconstruction_config["epsilon"]),
        initial_activity_bq=initial,
        relative_change_stop=reconstruction_config.get("relative_change_stop"),
        stop_patience=int(reconstruction_config.get("stop_patience", 3)),
    )
    gate_estimate, gate_history = mlem(
        operator,
        y_gate,
        int(reconstruction_config["iterations"]),
        float(reconstruction_config["epsilon"]),
        initial_activity_bq=initial,
        relative_change_stop=reconstruction_config.get("relative_change_stop"),
        stop_patience=int(reconstruction_config.get("stop_patience", 3)),
    )
    metadata = json.loads((PROJECT_ROOT / "results/phantom/phantom_metadata.json").read_text(encoding="utf-8"))
    hot_mask = np.asarray(metadata["hot_mask"], dtype=bool)
    background_mask = ~hot_mask
    predicted_synthetic = operator @ synthetic_estimate
    predicted_gate = operator @ gate_estimate
    metrics_synthetic = reconstruction_metrics(
        truth, synthetic_estimate, hot_mask, background_mask, poisson, predicted_synthetic
    )
    metrics_gate = reconstruction_metrics(
        truth, gate_estimate, hot_mask, background_mask, y_gate, predicted_gate
    )

    results = PROJECT_ROOT / "results"
    save_npy(results / "projections/expected_counts.npy", expected)
    save_npy(results / "projections/synthetic_poisson_counts.npy", poisson)
    save_npy(results / "projections/independent_gate_singles_counts.npy", y_gate)
    save_npy(results / "reconstruction/synthetic_mlem_activity_bq.npy", synthetic_estimate)
    save_npy(results / "reconstruction/independent_gate_mlem_activity_bq.npy", gate_estimate)
    save_npy(results / "reconstruction/synthetic_mlem_history_bq.npy", np.asarray(synthetic_history["estimate_history_bq"]))
    save_npy(results / "reconstruction/independent_gate_mlem_history_bq.npy", np.asarray(gate_history["estimate_history_bq"]))
    save_npy(results / "projections/synthetic_mlem_predicted_counts.npy", predicted_synthetic)
    save_npy(results / "projections/gate_mlem_predicted_counts.npy", predicted_gate)
    write_csv(
        results / "projections/measurement_vectors.csv",
        [
            {"row_id": i, "expected_counts": float(expected[i]),
             "synthetic_poisson_counts": int(poisson[i]),
             "independent_gate_singles": int(y_gate[i]),
             "synthetic_mlem_predicted_counts": float(predicted_synthetic[i]),
             "gate_mlem_predicted_counts": float(predicted_gate[i])}
            for i in range(y_gate.size)
        ],
        ["row_id", "expected_counts", "synthetic_poisson_counts", "independent_gate_singles",
         "synthetic_mlem_predicted_counts", "gate_mlem_predicted_counts"],
    )
    write_csv(results / "phantom/phantom_measurement_counts.csv", measurements, [
        "row_id", "pose_id", "task_id", "raw_singles_count", "raw_hits_count",
        "seed", "completion_path", "singles_sha256",
    ])
    write_runtime_json(results / "reconstruction/synthetic_mlem_history.json", synthetic_history)
    write_runtime_json(results / "reconstruction/independent_gate_mlem_history.json", gate_history)
    write_runtime_json(results / "reconstruction/synthetic_metrics.json", metrics_synthetic)
    write_runtime_json(results / "reconstruction/independent_gate_metrics.json", metrics_gate)
    plots = plot_reconstruction_results(
        PROJECT_ROOT, read_csv(PROJECT_ROOT / "runtime/manifests/image_voxel_map.csv"),
        phantom_image, expected, poisson, y_gate, synthetic_estimate, gate_estimate,
        synthetic_history, gate_history, predicted_synthetic, predicted_gate, metrics_gate,
    )
    summary = {
        "measurement_mode": "independent Gate phantom Singles by physical detector-pose exposure",
        "phantom_gate_tasks": len(measurements),
        "gate_singles_total": int(y_gate.sum()),
        "gate_hits_total": int(sum(row["raw_hits_count"] for row in measurements)),
        "expected_projection_counts_total": float(expected.sum()),
        "synthetic_poisson_counts_total": int(poisson.sum()),
        "synthetic_reconstruction_metrics": metrics_synthetic,
        "independent_gate_reconstruction_metrics": metrics_gate,
        "synthetic_mlem_iterations": synthetic_history["completed_iterations"],
        "independent_gate_mlem_iterations": gate_history["completed_iterations"],
        "reconstruction_settings": reconstruction_config,
        "post_filter": "disabled",
        "generated_plots": plots,
        "scientific_note": "The synthetic Poisson reconstruction uses H to generate and reconstruct its data; only the independently simulated Gate phantom vector is an experimental Monte Carlo measurement.",
    }
    write_runtime_json(PROJECT_ROOT / "runtime/provenance/reconstruction.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    try:
        reconstruct()
    except Exception as error:
        print(f"Phantom reconstruction failed: {error}", file=sys.stderr)
        raise SystemExit(1)
