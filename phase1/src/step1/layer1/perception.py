from __future__ import annotations

from phase1.src.step1.config import ALLOWED_SEGMENTATION_METHODS
from phase1.src.step1.data.models import Grid, PerceptionOutput, SegmentationPlan
from phase1.src.step1.layer1.objects import build_object, build_whole_grid_object, extract_cc_objects
from phase1.src.step1.layer1.relations import extract_relations


def build_segmentation_plan(grid: Grid, method: str) -> SegmentationPlan:
    if method not in ALLOWED_SEGMENTATION_METHODS:
        raise ValueError(f"Unsupported segmentation method in Step 1: {method}")

    if method == "whole_grid":
        objects = [build_whole_grid_object(grid)]
    else:
        connectivity = 4 if method == "cc4" else 8
        components = extract_cc_objects(grid, connectivity)
        objects = [build_object(f"{method}:{index}", component, grid) for index, component in enumerate(components)]
    return SegmentationPlan(
        plan_id=method,
        method=method,
        objects=objects,
        relations=extract_relations(objects),
    )


def perceive_grid(grid: Grid) -> PerceptionOutput:
    plans = [build_segmentation_plan(grid, method) for method in ALLOWED_SEGMENTATION_METHODS]
    return PerceptionOutput(segmentation_plans=plans)
