from __future__ import annotations

from phase1.src.step1.data.models import Alignment, ObjectData, SegmentationPlan
from phase1.src.step1.utils.ids import make_alignment_family_id, make_alignment_id


def align_objects(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    pair_index: int,
) -> list[Alignment]:
    methods = (
        ("pixel_overlap", _pixel_overlap_matches),
        ("color_shape", _color_shape_matches),
        ("bipartite", _bipartite_matches),
    )
    alignments: list[Alignment] = []
    for method_name, matcher in methods:
        matches = matcher(input_plan.objects, output_plan.objects)
        if not matches:
            continue
        matched_input = {input_id for input_id, _, _ in matches}
        matched_output = {output_id for _, output_id, _ in matches}
        alignments.append(
            Alignment(
                alignment_id=make_alignment_id(input_plan.plan_id, method_name, pair_index),
                alignment_family_id=make_alignment_family_id(input_plan.plan_id, method_name),
                matched_pairs=matches,
                unmatched_input=[obj.id for obj in input_plan.objects if obj.id not in matched_input],
                unmatched_output=[obj.id for obj in output_plan.objects if obj.id not in matched_output],
                merge_groups=[],
                split_groups=[],
            )
        )
    return alignments


def _pixel_overlap_matches(
    input_objects: list[ObjectData],
    output_objects: list[ObjectData],
) -> list[tuple[str, str, float]]:
    candidates: list[tuple[int, str, str]] = []
    for input_obj in input_objects:
        for output_obj in output_objects:
            overlap = len(input_obj.pixels & output_obj.pixels)
            if overlap > 0:
                candidates.append((overlap, input_obj.id, output_obj.id))
    return _greedy_unique_matches(sorted(candidates, key=lambda item: (-item[0], item[1], item[2])))


def _color_shape_matches(
    input_objects: list[ObjectData],
    output_objects: list[ObjectData],
) -> list[tuple[str, str, float]]:
    candidates: list[tuple[int, str, str]] = []
    for input_obj in input_objects:
        input_signature = _shape_signature(input_obj)
        for output_obj in output_objects:
            if input_signature != _shape_signature(output_obj):
                continue
            if input_obj.attrs.get("dominant_color") != output_obj.attrs.get("dominant_color"):
                continue
            candidates.append((len(input_obj.pixels), input_obj.id, output_obj.id))
    return _greedy_unique_matches(sorted(candidates, key=lambda item: (-item[0], item[1], item[2])))


def _bipartite_matches(
    input_objects: list[ObjectData],
    output_objects: list[ObjectData],
) -> list[tuple[str, str, float]]:
    if not input_objects or not output_objects:
        return []

    costs = [
        [_match_cost(input_obj, output_obj) for output_obj in output_objects]
        for input_obj in input_objects
    ]
    pair_indices = _hungarian_assignment(costs)
    matches: list[tuple[str, str, float]] = []
    for input_index, output_index in pair_indices:
        similarity = 1.0 / (1.0 + costs[input_index][output_index])
        matches.append((input_objects[input_index].id, output_objects[output_index].id, similarity))
    return sorted(matches, key=lambda item: item[0])


def _shape_signature(obj: ObjectData) -> tuple[int, int, int]:
    return (
        int(obj.attrs.get("area", len(obj.pixels))),
        int(obj.attrs.get("height", obj.bbox[2] - obj.bbox[0] + 1)),
        int(obj.attrs.get("width", obj.bbox[3] - obj.bbox[1] + 1)),
    )


def _greedy_unique_matches(candidates: list[tuple[int, str, str]]) -> list[tuple[str, str, float]]:
    used_input: set[str] = set()
    used_output: set[str] = set()
    matches: list[tuple[str, str, float]] = []
    for score, input_id, output_id in candidates:
        if input_id in used_input or output_id in used_output:
            continue
        used_input.add(input_id)
        used_output.add(output_id)
        matches.append((input_id, output_id, float(score)))
    return matches


def _match_cost(input_obj: ObjectData, output_obj: ObjectData) -> int:
    color_penalty = 0 if input_obj.attrs.get("dominant_color") == output_obj.attrs.get("dominant_color") else 100
    area_penalty = abs(int(input_obj.attrs.get("area", 0)) - int(output_obj.attrs.get("area", 0))) * 10
    row_penalty = int(abs(float(input_obj.attrs.get("center_row", 0.0)) - float(output_obj.attrs.get("center_row", 0.0))))
    col_penalty = int(abs(float(input_obj.attrs.get("center_col", 0.0)) - float(output_obj.attrs.get("center_col", 0.0))))
    return color_penalty + area_penalty + row_penalty + col_penalty


def _hungarian_assignment(costs: list[list[int]]) -> list[tuple[int, int]]:
    row_count = len(costs)
    col_count = len(costs[0])
    size = max(row_count, col_count)
    max_cost = max(max(row) for row in costs) if costs else 0
    pad_cost = max_cost + 10_000

    matrix = [[pad_cost for _ in range(size)] for _ in range(size)]
    for row_index in range(row_count):
        for col_index in range(col_count):
            matrix[row_index][col_index] = costs[row_index][col_index]

    u = [0] * (size + 1)
    v = [0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)

    for row_index in range(1, size + 1):
        p[0] = row_index
        col0 = 0
        minv = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[col0] = True
            row0 = p[col0]
            delta = float("inf")
            col1 = 0
            for col_index in range(1, size + 1):
                if used[col_index]:
                    continue
                cur = matrix[row0 - 1][col_index - 1] - u[row0] - v[col_index]
                if cur < minv[col_index]:
                    minv[col_index] = cur
                    way[col_index] = col0
                if minv[col_index] < delta:
                    delta = minv[col_index]
                    col1 = col_index
            for col_index in range(size + 1):
                if used[col_index]:
                    u[p[col_index]] += delta
                    v[col_index] -= delta
                else:
                    minv[col_index] -= delta
            col0 = col1
            if p[col0] == 0:
                break
        while True:
            col1 = way[col0]
            p[col0] = p[col1]
            col0 = col1
            if col0 == 0:
                break

    assignment: list[tuple[int, int]] = []
    for col_index in range(1, size + 1):
        row_index = p[col_index]
        if row_index == 0:
            continue
        row = row_index - 1
        col = col_index - 1
        if row < row_count and col < col_count:
            assignment.append((row, col))
    return sorted(assignment)
