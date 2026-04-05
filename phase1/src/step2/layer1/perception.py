from __future__ import annotations

from phase1.src.step2.config import ALLOWED_SEGMENTATION_METHODS, ENABLE_NESTED_SEGMENTATION
from phase1.src.step2.data.models import Grid, PerceptionOutput, SegmentationPlan
from phase1.src.step2.layer1.objects import build_object, build_whole_grid_object, extract_cc_objects
from phase1.src.step2.layer1.relations import extract_relations


def build_segmentation_plan(grid: Grid, method: str) -> SegmentationPlan:
    if method not in ALLOWED_SEGMENTATION_METHODS:
        raise ValueError(f"Unsupported segmentation method in Step 1: {method}")

    if method == "whole_grid":
        objects = [build_whole_grid_object(grid)]
        bg_color = None
    elif method == "bg_fg":
        bg_color = _dominant_background_color(grid)
        masked_grid = [
            [0 if value == bg_color else value for value in row]
            for row in grid
        ]
        components = extract_cc_objects(masked_grid, 4, same_color=True)
        objects = [build_object(f"{method}:{index}", component, grid) for index, component in enumerate(components)]
    else:
        connectivity = 4 if method == "cc4" else 8
        components = extract_cc_objects(grid, connectivity)
        objects = [build_object(f"{method}:{index}", component, grid) for index, component in enumerate(components)]
        bg_color = None
    return SegmentationPlan(
        plan_id=method,
        method=method,
        objects=objects,
        relations=extract_relations(objects),
        bg_color=bg_color,
    )


def perceive_grid(grid: Grid) -> PerceptionOutput:
    methods = list(ALLOWED_SEGMENTATION_METHODS)
    if ENABLE_NESTED_SEGMENTATION:
        methods.append("nested")
    plans = [build_segmentation_plan(grid, method) for method in methods]
    return PerceptionOutput(segmentation_plans=plans)


def _dominant_background_color(grid: Grid) -> int:
    color_counts: dict[int, int] = {}
    for row in grid:
        for value in row:
            color_counts[value] = color_counts.get(value, 0) + 1
    return min(color_counts, key=lambda color: (-color_counts[color], color))
