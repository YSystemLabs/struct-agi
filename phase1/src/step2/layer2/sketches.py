from __future__ import annotations

from collections import Counter

from phase1.src.step2.data.models import CandidateConstraint, CandidateSet, CandidateTransform, ObjectData, SegmentationPlan
from phase1.src.step2.layer2.diff import classify_object_diff, match_extend_to_boundary_directions
from phase1.src.step2.layer4.dsl import CopyBlock, CopyClause, PrimitiveCall, Step1Program, render_program
from phase1.src.step2.utils.ids import make_pair_transform_id


def generate_candidate_transforms(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    alignment: object,
    pair_index: int,
) -> list[CandidateTransform]:
    input_by_id = {obj.id: obj for obj in input_plan.objects}
    output_by_id = {obj.id: obj for obj in output_plan.objects}
    transforms: list[CandidateTransform] = []
    local_index = 0
    for input_id, output_id, score in alignment.matched_pairs:
        input_obj = input_by_id[input_id]
        output_obj = output_by_id[output_id]
        diff_type = classify_object_diff(input_obj, output_obj, input_plan.objects)
        for program in _programs_for_diff(diff_type, input_obj, output_obj, input_plan, output_plan):
            transforms.append(
                CandidateTransform(
                    transform_id=make_pair_transform_id(alignment.alignment_id, local_index),
                    alignment_id=alignment.alignment_id,
                    alignment_family_id=alignment.alignment_family_id,
                    program=program,
                    applicable_pairs=[pair_index],
                    match_score=float(score),
                )
            )
            local_index += 1

    for input_id in alignment.unmatched_input:
        input_obj = input_by_id[input_id]
        for program in _delete_programs(input_obj, input_plan):
            transforms.append(
                CandidateTransform(
                    transform_id=make_pair_transform_id(alignment.alignment_id, local_index),
                    alignment_id=alignment.alignment_id,
                    alignment_family_id=alignment.alignment_family_id,
                    program=program,
                    applicable_pairs=[pair_index],
                    match_score=0.0,
                )
            )
            local_index += 1
    return transforms


def build_candidate_set(
    plan_id: str,
    alignments: list[object],
    transforms: list[CandidateTransform],
    constraints: list[CandidateConstraint],
) -> CandidateSet:
    return CandidateSet(
        plan_id=plan_id,
        candidate_alignments=list(alignments),
        candidate_transforms=list(transforms),
        candidate_constraints=list(constraints),
    )


def _programs_for_diff(
    diff_type: str,
    input_obj: ObjectData,
    output_obj: ObjectData,
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
) -> list[Step1Program]:
    programs: list[Step1Program] = []
    programs.extend(_crop_programs(input_obj, output_obj, input_plan, output_plan))
    programs.extend(_restricted_translate_programs(diff_type, input_obj, output_obj, input_plan, output_plan))

    if diff_type == "copy":
        programs.append(Step1Program(copy_block=CopyBlock(target=input_obj.id, on_copy=CopyClause(), on_original=CopyClause())))
        if _is_largest_object(input_obj, input_plan) and input_plan.method == "bg_fg":
            programs.append(
                Step1Program(copy_block=CopyBlock(target="largest_object", on_copy=CopyClause(), on_original=CopyClause()))
            )
        if _is_smallest_object(input_obj, input_plan):
            programs.append(
                Step1Program(
                    copy_block=CopyBlock(
                        target="smallest_object",
                        on_copy=CopyClause(
                            primitives=(
                                PrimitiveCall(
                                    "translate",
                                    params={
                                        "dx": "to_largest_object_center_dx",
                                        "dy": "to_largest_object_center_dy",
                                    },
                                ),
                            ),
                        ),
                        on_original=CopyClause(),
                    )
                )
            )
        return _dedupe_programs(programs)
    if diff_type in {"translate", "boundary_translate"}:
        dy = output_obj.bbox[0] - input_obj.bbox[0]
        dx = output_obj.bbox[1] - input_obj.bbox[1]
        translate_params = _translate_param_candidates(input_obj, dx, dy, input_plan.objects)
        for params in translate_params:
            programs.append(
                Step1Program(primitives=(PrimitiveCall("translate", target="all", params=params),))
            )
            programs.append(
                Step1Program(primitives=(PrimitiveCall("translate", target=input_obj.id, params=params),))
            )
            if _is_largest_object(input_obj, input_plan) and input_plan.method == "bg_fg":
                programs.append(
                    Step1Program(primitives=(PrimitiveCall("translate", target="largest_object", params=params),))
                )
            programs.append(
                Step1Program(
                    copy_block=CopyBlock(
                        target=input_obj.id,
                        on_copy=CopyClause(
                            primitives=(PrimitiveCall("translate", params=params),),
                        ),
                        on_original=CopyClause(),
                    )
                )
            )
            if _is_largest_object(input_obj, input_plan) and input_plan.method == "bg_fg":
                programs.append(
                    Step1Program(
                        copy_block=CopyBlock(
                            target="largest_object",
                            on_copy=CopyClause(
                                primitives=(PrimitiveCall("translate", params=params),),
                            ),
                            on_original=CopyClause(),
                        )
                    )
                )
            programs.append(
                Step1Program(
                    copy_block=CopyBlock(
                        target="all",
                        on_copy=CopyClause(
                            primitives=(PrimitiveCall("translate", params=params),),
                        ),
                        on_original=CopyClause(),
                    )
                )
            )
        if _is_smallest_object(input_obj, input_plan):
            anchor_params = {
                "dx": "to_largest_object_center_dx",
                "dy": "to_largest_object_center_dy",
            }
            programs.append(
                Step1Program(primitives=(PrimitiveCall("translate", target="smallest_object", params=anchor_params),))
            )
            programs.append(
                Step1Program(
                    copy_block=CopyBlock(
                        target="smallest_object",
                        on_copy=CopyClause(primitives=(PrimitiveCall("translate", params=anchor_params),)),
                        on_original=CopyClause(),
                    )
                )
            )
        if _is_rare_color_object(input_obj, input_plan):
            programs.append(
                Step1Program(
                    primitives=(
                        PrimitiveCall(
                            "translate",
                            target="rare_color_object",
                            params={"dx": "to_input_center_dx", "dy": "to_input_center_dy"},
                        ),
                    )
                )
            )
            programs.append(
                Step1Program(
                    primitives=(
                        PrimitiveCall(
                            "translate",
                            target="rare_color_object",
                            params={"dx": "to_largest_object_center_dx", "dy": "to_largest_object_center_dy"},
                        ),
                    )
                )
            )
        return _dedupe_programs(programs)
    if diff_type == "extend_to_boundary":
        specs = match_extend_to_boundary_directions(input_obj, output_obj, input_plan.objects)
        for source, direction in specs:
            programs.append(
                Step1Program(
                    primitives=(
                        PrimitiveCall(
                            "extend_to_boundary",
                            target=input_obj.id,
                            params={"source": source, "direction": direction},
                        ),
                    )
                )
            )
            if _is_center_object(input_obj, input_plan):
                programs.append(
                    Step1Program(
                        primitives=(
                            PrimitiveCall(
                                "extend_to_boundary",
                                target="center_object",
                                params={"source": source, "direction": direction},
                            ),
                        )
                    )
                )
            if _is_largest_object(input_obj, input_plan) and input_plan.method == "bg_fg":
                programs.append(
                    Step1Program(
                        primitives=(
                            PrimitiveCall(
                                "extend_to_boundary",
                                target="largest_object",
                                params={"source": source, "direction": direction},
                            ),
                        )
                    )
                )
            if _is_smallest_object(input_obj, input_plan):
                programs.append(
                    Step1Program(
                        primitives=(
                            PrimitiveCall(
                                "extend_to_boundary",
                                target="smallest_object",
                                params={"source": source, "direction": direction},
                            ),
                        )
                    )
                )
            if _is_rare_color_object(input_obj, input_plan):
                programs.append(
                    Step1Program(
                        primitives=(
                            PrimitiveCall(
                                "extend_to_boundary",
                                target="rare_color_object",
                                params={"source": source, "direction": direction},
                            ),
                        )
                    )
                )
            if _is_gap_thinner_object(input_obj, input_plan):
                programs.append(
                    Step1Program(
                        primitives=(
                            PrimitiveCall(
                                "extend_to_boundary",
                                target="gap_thinner_object",
                                params={"source": source, "direction": direction},
                            ),
                        )
                    )
                )
        return _dedupe_programs(programs)
    if diff_type == "recolor":
        color = int(output_obj.attrs.get("dominant_color", 0))
        return [Step1Program(primitives=(PrimitiveCall("recolor", target=input_obj.id, params={"color": color}),))]
    if diff_type == "fill":
        color = int(output_obj.attrs.get("dominant_color", 0))
        programs = []
        if _is_center_cell_fill(input_obj, output_obj):
            programs.append(
                Step1Program(
                    primitives=(PrimitiveCall("fill", target="all", params={"mode": "center_cell"}),)
                )
            )
            programs.append(
                Step1Program(
                    primitives=(PrimitiveCall("fill", target=input_obj.id, params={"mode": "center_cell"}),)
                )
            )
        programs.append(
            Step1Program(primitives=(PrimitiveCall("fill", target=input_obj.id, params={"mode": "bbox_holes", "color": color}),))
        )
        return programs
    if diff_type == "crop":
        mode = "center_cell" if int(output_obj.attrs.get("area", 0)) == 1 else "tight_bbox"
        return [Step1Program(primitives=(PrimitiveCall("crop", target=input_obj.id, params={"mode": mode}),))]
    if diff_type == "rotate_or_flip":
        return [Step1Program(primitives=(PrimitiveCall("rotate", target=input_obj.id, params={"quarter_turns": 1}),))]
    programs.extend(_delete_programs(input_obj, input_plan))
    return _dedupe_programs(programs)

def _is_center_cell_fill(input_obj: ObjectData, output_obj: ObjectData) -> bool:
    added_pixels = output_obj.pixels - input_obj.pixels
    if len(added_pixels) != 1:
        return False
    min_row, min_col, max_row, max_col = output_obj.bbox
    center_cell = ((min_row + max_row) // 2, (min_col + max_col) // 2)
    return next(iter(added_pixels)) == center_cell


def _crop_programs(
    input_obj: ObjectData,
    output_obj: ObjectData,
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
) -> list[Step1Program]:
    if not _matches_tight_bbox_output(input_obj, output_obj, output_plan):
        return []
    programs = [Step1Program(primitives=(PrimitiveCall("crop", target=input_obj.id, params={"mode": "tight_bbox"}),))]
    if _is_center_object(input_obj, input_plan):
        programs.append(
            Step1Program(primitives=(PrimitiveCall("crop", target="center_object", params={"mode": "tight_bbox"}),))
        )
    if _is_largest_object(input_obj, input_plan) and input_plan.method == "bg_fg":
        programs.append(
            Step1Program(primitives=(PrimitiveCall("crop", target="largest_object", params={"mode": "tight_bbox"}),))
        )
    return programs


def _delete_programs(input_obj: ObjectData, input_plan: SegmentationPlan) -> list[Step1Program]:
    programs = [Step1Program(primitives=(PrimitiveCall("delete", target=input_obj.id),))]
    if _is_center_object(input_obj, input_plan):
        programs.append(Step1Program(primitives=(PrimitiveCall("delete", target="center_object"),)))
        programs.append(
            Step1Program(
                primitives=(PrimitiveCall("delete", params={"mode": "input_center_component"}),)
            )
        )
    if _is_largest_object(input_obj, input_plan) and input_plan.method == "bg_fg":
        programs.append(Step1Program(primitives=(PrimitiveCall("delete", target="largest_object"),)))
    return _dedupe_programs(programs)


def _matches_tight_bbox_output(
    input_obj: ObjectData,
    output_obj: ObjectData,
    output_plan: SegmentationPlan,
) -> bool:
    if len(output_plan.objects) != 1:
        return False
    if output_obj.bbox[:2] != (0, 0):
        return False
    min_row = min(row for row, _ in input_obj.pixels)
    min_col = min(col for _, col in input_obj.pixels)
    normalized = {(row - min_row, col - min_col) for row, col in input_obj.pixels}
    return normalized == output_obj.pixels


def _restricted_translate_programs(
    diff_type: str,
    input_obj: ObjectData,
    output_obj: ObjectData,
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
) -> list[Step1Program]:
    if _should_add_rare_color_motif_translate(diff_type, input_obj, output_obj, input_plan, output_plan):
        return [
            Step1Program(
                primitives=(
                    PrimitiveCall(
                        "translate",
                        params={"mode": "rare_color_motif_to_largest_component_center"},
                    ),
                )
            )
        ]
    return []


def _should_add_rare_color_motif_translate(
    diff_type: str,
    input_obj: ObjectData,
    output_obj: ObjectData,
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
) -> bool:
    if diff_type == "translate" and _is_rare_color_object(input_obj, input_plan):
        return True
    if len(input_plan.objects) != 1 or len(output_plan.objects) != 1:
        return False
    if input_obj.pixels == output_obj.pixels:
        return False
    if input_obj.bbox != output_obj.bbox:
        return False
    if int(input_obj.attrs.get("area", 0)) != int(output_obj.attrs.get("area", 0)):
        return False
    return int(input_obj.attrs.get("dominant_color", 0)) == int(output_obj.attrs.get("dominant_color", 0))


def _translate_param_candidates(
    input_obj: ObjectData,
    dx: int,
    dy: int,
    context_objects: list[ObjectData],
) -> list[dict[str, int | str]]:
    params = [{"dy": dy, "dx": dx}]
    symbolic_dx = _match_symbolic_offset(dx, input_obj, axis="x")
    symbolic_dy = _match_symbolic_offset(dy, input_obj, axis="y")
    if symbolic_dx is not None or symbolic_dy is not None:
        params.append(
            {
                "dy": symbolic_dy if symbolic_dy is not None else dy,
                "dx": symbolic_dx if symbolic_dx is not None else dx,
            }
        )
    boundary_offsets = _boundary_offsets(input_obj, context_objects)
    if boundary_offsets is not None and boundary_offsets == (dx, dy):
        params.append({"dx": "to_boundary_dx", "dy": "to_boundary_dy"})
    nearest_object_offsets = _nearest_object_offsets(input_obj, context_objects)
    if nearest_object_offsets is not None and nearest_object_offsets == (dx, dy):
        params.append({"dx": "to_nearest_object_dx", "dy": "to_nearest_object_dy"})

    deduped: list[dict[str, int | str]] = []
    seen: set[tuple[tuple[str, int | str], ...]] = set()
    for candidate in params:
        key = tuple(sorted(candidate.items()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _match_symbolic_offset(offset: int, input_obj: ObjectData, axis: str) -> str | None:
    candidates: list[tuple[str, int]] = []
    if axis == "x":
        candidates = [
            ("input_width", int(input_obj.attrs.get("canvas_width", 0))),
            ("object_width", int(input_obj.attrs.get("width", 0))),
        ]
    else:
        candidates = [
            ("input_height", int(input_obj.attrs.get("canvas_height", 0))),
            ("object_height", int(input_obj.attrs.get("height", 0))),
        ]
    for symbol, value in candidates:
        if offset == value:
            return symbol
        if offset == -value:
            return f"-{symbol}"
    return None


def _boundary_offsets(input_obj: ObjectData, context_objects: list[ObjectData]) -> tuple[int, int] | None:
    canvas_height = int(input_obj.attrs.get("canvas_height", 0))
    canvas_width = int(input_obj.attrs.get("canvas_width", 0))
    if canvas_height <= 0 or canvas_width <= 0:
        return None
    direction = _boundary_direction(input_obj, context_objects)
    min_row, min_col, max_row, max_col = input_obj.bbox
    if direction == "up":
        return (0, -min_row)
    if direction == "down":
        return (0, canvas_height - 1 - max_row)
    if direction == "left":
        return (-min_col, 0)
    return (canvas_width - 1 - max_col, 0)


def _nearest_object_offsets(input_obj: ObjectData, context_objects: list[ObjectData]) -> tuple[int, int] | None:
    others = [obj for obj in context_objects if obj.id != input_obj.id]
    if not others:
        return None
    mover = _nearest_object_mover(context_objects)
    if mover is None or mover.id != input_obj.id:
        return None

    best: tuple[tuple[int, int, int, str], tuple[int, int]] | None = None
    min_row, min_col, max_row, max_col = input_obj.bbox
    for other in others:
        other_min_row, other_min_col, other_max_row, other_max_col = other.bbox
        candidates: list[tuple[int, int]] = []
        if _overlap_1d(min_row, max_row, other_min_row, other_max_row):
            candidates.append((other_min_col - max_col - 1, 0))
            candidates.append((other_max_col - min_col + 1, 0))
        if _overlap_1d(min_col, max_col, other_min_col, other_max_col):
            candidates.append((0, other_min_row - max_row - 1))
            candidates.append((0, other_max_row - min_row + 1))
        if not candidates:
            candidates.extend(
                [
                    (other_min_col - max_col - 1, other_min_row - max_row - 1),
                    (other_min_col - max_col - 1, other_max_row - min_row + 1),
                    (other_max_col - min_col + 1, other_min_row - max_row - 1),
                    (other_max_col - min_col + 1, other_max_row - min_row + 1),
                ]
            )
        for dx, dy in candidates:
            score = (abs(dx) + abs(dy), abs(dy), abs(dx), other.id)
            if best is None or score < best[0]:
                best = (score, (dx, dy))
    return best[1] if best is not None else None


def _boundary_direction(input_obj: ObjectData, context_objects: list[ObjectData]) -> str:
    if len(context_objects) == 1:
        return _single_object_boundary_direction(input_obj)

    largest = max(context_objects, key=lambda obj: (int(obj.attrs.get("area", 0)), tuple(-value for value in obj.bbox), obj.id))
    height = largest.bbox[2] - largest.bbox[0] + 1
    width = largest.bbox[3] - largest.bbox[1] + 1
    if height > width:
        top_distance = sum(obj.bbox[0] for obj in context_objects)
        bottom_distance = sum(int(obj.attrs.get("canvas_height", 0)) - 1 - obj.bbox[2] for obj in context_objects)
        return "up" if top_distance <= bottom_distance else "down"
    if width > height:
        left_distance = sum(obj.bbox[1] for obj in context_objects)
        right_distance = sum(int(obj.attrs.get("canvas_width", 0)) - 1 - obj.bbox[3] for obj in context_objects)
        return "left" if left_distance <= right_distance else "right"
    return _single_object_boundary_direction(largest)


def _single_object_boundary_direction(input_obj: ObjectData) -> str:
    min_row, min_col, max_row, max_col = input_obj.bbox
    height = max_row - min_row + 1
    width = max_col - min_col + 1
    top_edge = sum(1 for row, _ in input_obj.pixels if row == min_row)
    bottom_edge = sum(1 for row, _ in input_obj.pixels if row == max_row)
    if width > height and bottom_edge != top_edge:
        return "right" if bottom_edge > top_edge else "left"

    mid_row = (min_row + max_row) / 2
    mid_col = (min_col + max_col) / 2
    top_half = sum(1 for row, _ in input_obj.pixels if row < mid_row)
    bottom_half = sum(1 for row, _ in input_obj.pixels if row > mid_row)
    left_half = sum(1 for _, col in input_obj.pixels if col < mid_col)
    right_half = sum(1 for _, col in input_obj.pixels if col > mid_col)
    if abs(left_half - right_half) >= abs(top_half - bottom_half) and left_half != right_half:
        return "right" if left_half > right_half else "left"
    if top_half != bottom_half:
        return "down" if top_half > bottom_half else "up"
    return "right"


def _nearest_object_mover(context_objects: list[ObjectData]) -> ObjectData | None:
    if len(context_objects) < 2:
        return None
    best: tuple[int, float, int, int, str] | None = None
    chosen: ObjectData | None = None
    for index, obj in enumerate(context_objects):
        for other in context_objects[index + 1 :]:
            gap = _bbox_gap(obj.bbox, other.bbox)
            for candidate in (obj, other):
                score = (
                    gap,
                    _grid_center_distance(candidate),
                    _boundary_touch_count(candidate),
                    int(candidate.attrs.get("area", 0)),
                    candidate.id,
                )
                if best is None or score < best:
                    best = score
                    chosen = candidate
    return chosen


def _grid_center_distance(obj: ObjectData) -> float:
    canvas_height = int(obj.attrs.get("canvas_height", 0))
    canvas_width = int(obj.attrs.get("canvas_width", 0))
    grid_center_row = (canvas_height - 1) / 2
    grid_center_col = (canvas_width - 1) / 2
    return abs(float(obj.attrs.get("center_row", 0.0)) - grid_center_row) + abs(
        float(obj.attrs.get("center_col", 0.0)) - grid_center_col
    )


def _boundary_touch_count(obj: ObjectData) -> int:
    canvas_height = int(obj.attrs.get("canvas_height", 0))
    canvas_width = int(obj.attrs.get("canvas_width", 0))
    min_row, min_col, max_row, max_col = obj.bbox
    return sum(
        (
            min_row == 0,
            min_col == 0,
            max_row == canvas_height - 1,
            max_col == canvas_width - 1,
        )
    )


def _bbox_gap(a_bbox: tuple[int, int, int, int], b_bbox: tuple[int, int, int, int]) -> int:
    a_min_row, a_min_col, a_max_row, a_max_col = a_bbox
    b_min_row, b_min_col, b_max_row, b_max_col = b_bbox
    row_gap = max(0, max(b_min_row - a_max_row - 1, a_min_row - b_max_row - 1))
    col_gap = max(0, max(b_min_col - a_max_col - 1, a_min_col - b_max_col - 1))
    return row_gap + col_gap


def _overlap_1d(a_min: int, a_max: int, b_min: int, b_max: int) -> bool:
    return not (a_max < b_min or b_max < a_min)


def _is_center_object(input_obj: ObjectData, input_plan: SegmentationPlan) -> bool:
    selected = _select_center_object(input_plan.objects, input_obj.attrs)
    return selected is not None and selected.id == input_obj.id


def _is_smallest_object(input_obj: ObjectData, input_plan: SegmentationPlan) -> bool:
    selected = min(input_plan.objects, key=lambda obj: (int(obj.attrs.get("area", 0)), obj.bbox, obj.id))
    return selected.id == input_obj.id


def _is_largest_object(input_obj: ObjectData, input_plan: SegmentationPlan) -> bool:
    selected = max(input_plan.objects, key=lambda obj: (int(obj.attrs.get("area", 0)), tuple(-value for value in obj.bbox), obj.id))
    return selected.id == input_obj.id


def _is_rare_color_object(input_obj: ObjectData, input_plan: SegmentationPlan) -> bool:
    color_counts = Counter(int(obj.attrs.get("dominant_color", 0)) for obj in input_plan.objects)
    selected = min(
        input_plan.objects,
        key=lambda obj: (
            color_counts[int(obj.attrs.get("dominant_color", 0))],
            int(obj.attrs.get("area", 0)),
            obj.bbox,
            obj.id,
        ),
    )
    return selected.id == input_obj.id


def _is_gap_thinner_object(input_obj: ObjectData, input_plan: SegmentationPlan) -> bool:
    selected = _select_gap_thinner_object(input_plan.objects)
    return selected is not None and selected.id == input_obj.id


def _select_gap_thinner_object(objects: list[ObjectData]) -> ObjectData | None:
    gap_pair = _select_single_axis_gap_pair(objects)
    if gap_pair is None:
        return None
    axis, first, second = gap_pair
    if axis == "vertical":
        return min(
            (first, second),
            key=lambda obj: (int(obj.attrs.get("width", 0)), int(obj.attrs.get("area", 0)), obj.id),
        )
    return min(
        (first, second),
        key=lambda obj: (int(obj.attrs.get("height", 0)), int(obj.attrs.get("area", 0)), obj.id),
    )


def _select_single_axis_gap_pair(objects: list[ObjectData]) -> tuple[str, ObjectData, ObjectData] | None:
    best: tuple[int, int, str, str] | None = None
    chosen: tuple[str, ObjectData, ObjectData] | None = None
    for index, obj in enumerate(objects):
        for other in objects[index + 1 :]:
            gap_info = _single_axis_gap_info(obj.bbox, other.bbox)
            if gap_info is None:
                continue
            axis, gap = gap_info
            score = (gap, 0 if axis == "vertical" else 1, obj.id, other.id)
            if best is None or score < best:
                best = score
                chosen = (axis, obj, other)
    return chosen


def _single_axis_gap_info(
    a_bbox: tuple[int, int, int, int],
    b_bbox: tuple[int, int, int, int],
) -> tuple[str, int] | None:
    a_min_row, a_min_col, a_max_row, a_max_col = a_bbox
    b_min_row, b_min_col, b_max_row, b_max_col = b_bbox
    row_gap = max(b_min_row - a_max_row - 1, a_min_row - b_max_row - 1)
    col_gap = max(b_min_col - a_max_col - 1, a_min_col - b_max_col - 1)
    if row_gap > 0 and col_gap <= 0 and _overlap_1d(a_min_col, a_max_col, b_min_col, b_max_col):
        return ("vertical", row_gap)
    if col_gap > 0 and row_gap <= 0 and _overlap_1d(a_min_row, a_max_row, b_min_row, b_max_row):
        return ("horizontal", col_gap)
    return None


def _select_center_object(objects: list[ObjectData], attrs: dict[str, int | float]) -> ObjectData | None:
    if not objects:
        return None
    grid_center_row = (int(attrs.get("canvas_height", 0)) - 1) / 2
    grid_center_col = (int(attrs.get("canvas_width", 0)) - 1) / 2
    return min(
        objects,
        key=lambda obj: (
            min(
                abs(row - grid_center_row) + abs(col - grid_center_col)
                for row, col in obj.pixels
            ),
            int(obj.attrs.get("area", 0)),
            obj.bbox,
            obj.id,
        ),
    )


def _dedupe_programs(programs: list[Step1Program]) -> list[Step1Program]:
    deduped: list[Step1Program] = []
    seen: set[str] = set()
    for program in programs:
        program_key = render_program(program)
        if program_key in seen:
            continue
        seen.add(program_key)
        deduped.append(program)
    return deduped
