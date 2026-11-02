from __future__ import annotations

from typing import Any


def evaluate_asci(config: dict[str, Any], poses: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "NOT PHYSICALLY APPLICABLE",
        "defined": False,
        "reason": config["analysis"]["asci_reason"],
        "reference_method": "occupied angular bins per image pixel divided by configured angular bins, after valid beam/FWHM/sensitivity filtering",
        "onecube_input_assessment": "The acquisition translates one uncollimated bare crystal. Pose-position azimuth does not encode a projection direction, and no directional response beam is measured.",
        "physical_pose_count": len(poses),
        "physical_pose_coordinate_extent_mm": {
            "x": [min(float(p["detector_x_mm"]) for p in poses), max(float(p["detector_x_mm"]) for p in poses)],
            "y": [min(float(p["detector_y_mm"]) for p in poses), max(float(p["detector_y_mm"]) for p in poses)],
        },
        "angular_coverage_map_generated": False,
        "separate_translation_pose_map": "results/plots/acquisition_design.png",
    }
