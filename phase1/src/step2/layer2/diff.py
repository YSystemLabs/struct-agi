from __future__ import annotations

from phase1.src.step2.data.models import ObjectData, SegmentationPlan
from phase1.src.step2.layer4.executor import _flip_pixels, _rotate_once


def classify_object_diff(input_obj: ObjectData, output_obj: ObjectData) -> str:
    if input_obj.pixels == output_obj.pixels:
        if input_obj.attrs.get("dominant_color") != output_obj.attrs.get("dominant_color"):
            return "recolor"
        return "copy"

    input_normalized = _normalize_pixels(input_obj.pixels)
    output_normalized = _normalize_pixels(output_obj.pixels)
    if input_normalized == output_normalized:
        return "translate"
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
        classify_object_diff(input_by_id[input_id], output_by_id[output_id])
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
