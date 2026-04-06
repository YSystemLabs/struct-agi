from __future__ import annotations

from phase1.src.step2.data.models import ObjectData, SegmentationPlan
from phase1.src.step2.layer4.executor import _extend_to_boundary_pixels, _flip_pixels, _rotate_once


def classify_object_diff(
    input_obj: ObjectData,
    output_obj: ObjectData,
    context_objects: list[ObjectData] | None = None,
) -> str:
    if input_obj.pixels == output_obj.pixels:
        if input_obj.attrs.get("dominant_color") != output_obj.attrs.get("dominant_color"):
            return "recolor"
        return "copy"

    input_normalized = _normalize_pixels(input_obj.pixels)
    output_normalized = _normalize_pixels(output_obj.pixels)
    if input_normalized == output_normalized:
        if _touches_canvas_boundary(output_obj) and not _touches_canvas_boundary(input_obj):
            return "boundary_translate"
        return "translate"
    if match_extend_to_boundary_directions(input_obj, output_obj, context_objects):
        return "extend_to_boundary"
    if input_normalized <= output_normalized:
        return "fill"
    if output_normalized <= input_normalized:
        return "crop"
    if _rotated_or_flipped_matches(input_normalized, output_normalized):
        return "rotate_or_flip"
    return "delete"


def classify_alignment_diffs(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    alignment: object,
) -> list[str]:
    input_by_id = {obj.id: obj for obj in input_plan.objects}
    output_by_id = {obj.id: obj for obj in output_plan.objects}
    diffs = [
        classify_object_diff(input_by_id[input_id], output_by_id[output_id], input_plan.objects)
        for input_id, output_id, _ in alignment.matched_pairs
    ]
    diffs.extend("delete" for _ in alignment.unmatched_input)
    diffs.extend("copy" for _ in alignment.unmatched_output)
    return diffs


def _normalize_pixels(pixels: set[tuple[int, int]]) -> set[tuple[int, int]]:
    if not pixels:
        return set()
    min_row = min(row for row, _ in pixels)
    min_col = min(col for _, col in pixels)
    return {(row - min_row, col - min_col) for row, col in pixels}


def _rotated_or_flipped_matches(
    input_pixels: set[tuple[int, int]],
    output_pixels: set[tuple[int, int]],
) -> bool:
    rotated = set(input_pixels)
    for _ in range(4):
        rotated = _normalize_pixels(_rotate_once(rotated))
        if rotated == output_pixels:
            return True
    return _normalize_pixels(_flip_pixels(input_pixels, "horizontal")) == output_pixels or _normalize_pixels(
        _flip_pixels(input_pixels, "vertical")
    ) == output_pixels


def _touches_canvas_boundary(obj: ObjectData) -> bool:
    canvas_height = int(obj.attrs.get("canvas_height", 0))
    canvas_width = int(obj.attrs.get("canvas_width", 0))
    if canvas_height <= 0 or canvas_width <= 0:
        return False
    min_row, min_col, max_row, max_col = obj.bbox
    return min_row == 0 or min_col == 0 or max_row == canvas_height - 1 or max_col == canvas_width - 1


def match_extend_to_boundary_directions(
    input_obj: ObjectData,
    output_obj: ObjectData,
    context_objects: list[ObjectData] | None = None,
) -> list[tuple[str, str]]:
    canvas_height = int(input_obj.attrs.get("canvas_height", 0))
    canvas_width = int(input_obj.attrs.get("canvas_width", 0))
    if canvas_height <= 0 or canvas_width <= 0:
        return []
    if not input_obj.pixels or not output_obj.pixels:
        return []
    if not input_obj.pixels < output_obj.pixels:
        return []

    blank_grid = [[0] * canvas_width for _ in range(canvas_height)]
    param_context = context_objects or [input_obj]
    matches: list[tuple[str, str]] = []
    for source in (
        "full_boundary",
        "top_edge",
        "bottom_edge",
        "left_edge",
        "right_edge",
        "center_row",
        "center_col",
    ):
        for direction in (
            "up",
            "down",
            "left",
            "right",
            "nearest_boundary",
            "to_nearest_object_boundary",
            "horizontal_both",
            "vertical_both",
        ):
            extended = _extend_to_boundary_pixels(input_obj, direction, blank_grid, param_context, source)
            if extended == output_obj.pixels:
                matches.append((source, direction))
    return matches
