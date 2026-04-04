from __future__ import annotations

from collections import Counter

from phase1.src.step1.data.models import CandidateConstraint, CandidateSet, CandidateTransform, ObjectData, SegmentationPlan
from phase1.src.step1.layer2.diff import classify_object_diff
from phase1.src.step1.layer4.dsl import CopyBlock, CopyClause, PrimitiveCall, Step1Program, render_program
from phase1.src.step1.utils.ids import make_pair_transform_id


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
        diff_type = classify_object_diff(input_obj, output_obj)
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
    if diff_type == "translate":
        dy = output_obj.bbox[0] - input_obj.bbox[0]
        dx = output_obj.bbox[1] - input_obj.bbox[1]
        translate_params = _translate_param_candidates(input_obj, dx, dy)
        for params in translate_params:
            programs.append(
                Step1Program(primitives=(PrimitiveCall("translate", target=input_obj.id, params=params),))
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


def _translate_param_candidates(input_obj: ObjectData, dx: int, dy: int) -> list[dict[str, int | str]]:
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
    return params


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


def _is_center_object(input_obj: ObjectData, input_plan: SegmentationPlan) -> bool:
    selected = _select_center_object(input_plan.objects, input_obj.attrs)
    return selected is not None and selected.id == input_obj.id


def _is_smallest_object(input_obj: ObjectData, input_plan: SegmentationPlan) -> bool:
    selected = min(input_plan.objects, key=lambda obj: (int(obj.attrs.get("area", 0)), obj.bbox, obj.id))
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
