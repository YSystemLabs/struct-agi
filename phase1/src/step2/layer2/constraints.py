from __future__ import annotations

from collections import defaultdict

from phase1.src.step2.config import ALLOWED_OUTPUT_SIZE_RULES
from phase1.src.step2.data.models import CandidateConstraint, SegmentationPlan
from phase1.src.step2.utils.ids import make_pair_constraint_id


def extract_constraints(
    input_plan: SegmentationPlan,
    output_plan: SegmentationPlan,
    alignment: object,
    pair_index: int,
) -> list[CandidateConstraint]:
    predicates: list[str] = []
    size_rule = _infer_size_rule(input_plan, output_plan)
    predicates.append(f"size_rule:{size_rule}")

    input_by_id = {obj.id: obj for obj in input_plan.objects}
    output_by_id = {obj.id: obj for obj in output_plan.objects}
    for input_id, output_id, _ in alignment.matched_pairs:
        src_color = int(input_by_id[input_id].attrs.get("dominant_color", 0))
        dst_color = int(output_by_id[output_id].attrs.get("dominant_color", 0))
        predicates.append(f"color_map:{src_color}->{dst_color}")

    matched_input = {input_id for input_id, _, _ in alignment.matched_pairs}
    matched_output = {output_id for _, output_id, _ in alignment.matched_pairs}
    if matched_input and matched_output:
        for source_id, target_id, relation_name in output_plan.relations:
            if source_id in matched_output and target_id in matched_output:
                predicates.append(f"relative_position:{relation_name}")

    constraints: list[CandidateConstraint] = []
    for index, predicate in enumerate(sorted(set(predicates))):
        constraints.append(
            CandidateConstraint(
                constraint_id=make_pair_constraint_id(alignment.alignment_id, index),
                alignment_id=alignment.alignment_id,
                alignment_family_id=alignment.alignment_family_id,
                predicate=predicate,
                holds_in=[pair_index],
            )
        )
    return constraints


def partition_constraints(
    constraints: list[CandidateConstraint],
    train_pair_count: int,
    relevant_pairs: list[int] | None = None,
    chosen_size_rule: str | None = None,
) -> dict[str, list[str]]:
    grouped = _group_constraints(constraints, relevant_pairs)

    size_rules = sorted(predicate for predicate in grouped if predicate.startswith("size_rule:"))
    if chosen_size_rule is not None and chosen_size_rule not in size_rules:
        raise ValueError(f"Requested size rule is not available for this constraint slice: {chosen_size_rule}")
    if chosen_size_rule is None and size_rules:
        chosen_size_rule = max(
            size_rules,
            key=lambda predicate: (len(grouped[predicate]), predicate),
        )

    strong: list[str] = []
    weak: list[str] = []
    for predicate in sorted(grouped):
        if predicate.startswith("size_rule:") and predicate != chosen_size_rule:
            weak.append(predicate)
            continue
        if len(grouped[predicate]) == train_pair_count:
            strong.append(predicate)
        else:
            weak.append(predicate)

    if chosen_size_rule is not None and chosen_size_rule not in strong:
        strong.insert(0, chosen_size_rule)
        if chosen_size_rule in weak:
            weak.remove(chosen_size_rule)

    if sum(1 for predicate in strong if predicate.startswith("size_rule:")) > 1:
        raise ValueError("Step 1 strong constraints must contain exactly one size_rule:*")

    for predicate in strong:
        if predicate.startswith("size_rule:"):
            rule = predicate.split(":", 1)[1]
            if rule not in ALLOWED_OUTPUT_SIZE_RULES:
                raise ValueError(f"Unsupported output size rule in strong constraints: {rule}")

    return {"strong": strong, "weak": weak}


def observed_size_rules(
    constraints: list[CandidateConstraint],
    relevant_pairs: list[int] | None = None,
) -> list[str]:
    grouped = _group_constraints(constraints, relevant_pairs)
    return sorted(predicate for predicate in grouped if predicate.startswith("size_rule:"))


def _infer_size_rule(input_plan: SegmentationPlan, output_plan: SegmentationPlan) -> str:
    input_shape = _plan_grid_shape(input_plan)
    output_shape = _plan_grid_shape(output_plan)
    if output_shape == input_shape:
        return "preserve_input_size"
    if output_shape == (1, 1):
        return "crop_center_cell"
    if (output_shape[0] * output_shape[1]) < (input_shape[0] * input_shape[1]):
        return "crop_selected_bbox"
    return "fit_transformed_extent"


def _plan_grid_shape(plan: SegmentationPlan) -> tuple[int, int]:
    if not plan.objects:
        return (0, 0)
    first = plan.objects[0]
    canvas_height = int(first.attrs.get("canvas_height", first.bbox[2] + 1))
    canvas_width = int(first.attrs.get("canvas_width", first.bbox[3] + 1))
    return (canvas_height, canvas_width)


def _group_constraints(
    constraints: list[CandidateConstraint],
    relevant_pairs: list[int] | None,
) -> dict[str, set[int]]:
    grouped: dict[str, set[int]] = defaultdict(set)
    pair_filter = set(relevant_pairs or [])
    use_pair_filter = relevant_pairs is not None
    for constraint in constraints:
        holds_in = set(constraint.holds_in)
        if use_pair_filter:
            holds_in &= pair_filter
        if not holds_in:
            continue
        grouped[constraint.predicate].update(holds_in)
    return grouped
