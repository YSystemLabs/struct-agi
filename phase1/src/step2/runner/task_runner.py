from __future__ import annotations

from pathlib import Path
from statistics import mean, median

from phase1.src.step2.config import STEP2_BEAM_SIZE, STEP2_TRAIN_TASKS
from phase1.src.step2.data.models import Alignment, ArcTask, Attribution, CandidateConstraint, CandidateTransform, Grid, Hypothesis, SearchStats, to_jsonable
from phase1.src.step2.layer1.perception import perceive_grid
from phase1.src.step2.layer2.alignment import align_objects
from phase1.src.step2.layer2.constraints import extract_constraints
from phase1.src.step2.layer2.sketches import build_candidate_set, generate_candidate_transforms
from phase1.src.step2.layer3.hypothesis import assemble_hypotheses
from phase1.src.step2.layer3.selector import apply_hypothesis_beam, clear_rendered_train_outputs, hypothesis_cache_key, select_best_hypothesis, set_rendered_train_outputs
from phase1.src.step2.layer4.dsl import Step1Program, parse_program, render_program
from phase1.src.step2.layer4.executor import execute_program
from phase1.src.step2.layer5.attribution import build_attribution
from phase1.src.step2.layer5.verify import classify_failure, pixel_accuracy, verify_constraints
from phase1.src.step2.utils.debug_dump import dump_task_debug_bundle
from phase1.src.step2.utils.ids import make_alignment_family_id, make_family_constraint_id, make_family_transform_id
from phase1.src.step2.utils.timing import timed_section


def run_task(task: ArcTask, output_dir: str | Path) -> Attribution:
    allowed_ids = {task_id for _, task_id, _ in STEP2_TRAIN_TASKS}
    if task.task_id not in allowed_ids:
        raise ValueError(f"Diagnostic or unknown task is not allowed in Step 2 runner: {task.task_id}")

    metrics: dict[str, int] = {}
    debug_bundle: dict[str, object] = {}

    with timed_section(metrics, "layer1_time_ms"):
        train_perception = [
            {
                "pair_index": pair.pair_index,
                "input": perceive_grid(pair.input),
                "output": perceive_grid(pair.output or pair.input),
            }
            for pair in task.train_pairs
        ]
    debug_bundle["layer1"] = [
        {
            "pair_index": item["pair_index"],
            "input": to_jsonable(item["input"]),
            "output": to_jsonable(item["output"]),
        }
        for item in train_perception
    ]
    debug_bundle["diagnostics"] = [
        {
            "pair_index": item["pair_index"],
            "input_plans": _plan_diagnostics(item["input"]),
            "output_plans": _plan_diagnostics(item["output"]),
        }
        for item in train_perception
    ]

    with timed_section(metrics, "layer2_time_ms"):
        family_buckets: dict[tuple[str, str], dict[str, object]] = {}
        for pair, pair_perception in zip(task.train_pairs, train_perception):
            input_plans = {plan.plan_id: plan for plan in pair_perception["input"].segmentation_plans}
            output_plans = {plan.plan_id: plan for plan in pair_perception["output"].segmentation_plans}
            for plan_id, input_plan in input_plans.items():
                output_plan = output_plans[plan_id]
                # bg_fg output may have 0 foreground objects when the output
                # grid is dominated by a non-zero colour (e.g. Center3).
                # Fall back to cc4 output objects so alignment can still form.
                if input_plan.method == "bg_fg" and len(output_plan.objects) == 0:
                    cc4_output = output_plans.get("cc4")
                    if cc4_output is not None and len(cc4_output.objects) > 0:
                        output_plan = cc4_output
                alignments = align_objects(input_plan, output_plan, pair.pair_index)
                for alignment in alignments:
                    transforms = generate_candidate_transforms(input_plan, output_plan, alignment, pair.pair_index)
                    constraints = extract_constraints(input_plan, output_plan, alignment, pair.pair_index)
                    _accumulate_candidate_family(family_buckets, plan_id, alignment, transforms, constraints)
        candidate_sets, layer2_debug = _materialize_candidate_sets(family_buckets)
    debug_bundle["layer2"] = layer2_debug

    with timed_section(metrics, "layer3_time_ms"):
        hypotheses = assemble_hypotheses(candidate_sets)
        evaluated_hypotheses, beam_saturated = apply_hypothesis_beam(hypotheses, STEP2_BEAM_SIZE)
        selected_hypothesis: Hypothesis | None = None
        selector_debug: dict[str, object] = {}
    rendered_train_outputs: dict[str, list[Grid]] = {}
    render_failures: dict[str, str] = {}
    with timed_section(metrics, "layer4_time_ms"):
        if evaluated_hypotheses:
            rendered_train_outputs, render_failures = _render_hypotheses_on_train(
                evaluated_hypotheses,
                task.train_pairs,
                train_perception,
            )
    with timed_section(metrics, "layer3_time_ms"):
        if evaluated_hypotheses:
            train_inputs = [pair.input for pair in task.train_pairs]
            train_outputs = [pair.output or pair.input for pair in task.train_pairs]
            set_rendered_train_outputs(rendered_train_outputs)
            try:
                selected_hypothesis, selector_debug = select_best_hypothesis(evaluated_hypotheses, train_inputs, train_outputs)
            finally:
                clear_rendered_train_outputs()
    debug_bundle["selected_hypothesis"] = {
        "hypothesis": to_jsonable(selected_hypothesis) if selected_hypothesis is not None else None,
        "beam": {
            "beam_size": STEP2_BEAM_SIZE,
            "beam_saturated": beam_saturated,
            "hypotheses_before_beam": len(hypotheses),
            "hypotheses_after_beam": len(evaluated_hypotheses),
        },
        "selector": selector_debug,
    }

    predictions: list[Grid] = []
    failure_detail: str | None = None
    execution_ok = False
    has_hypothesis = selected_hypothesis is not None

    if selected_hypothesis is not None:
        selected_key = hypothesis_cache_key(selected_hypothesis)
        predictions = rendered_train_outputs.get(selected_key, [])
        failure_detail = render_failures.get(selected_key)
        execution_ok = selected_key in rendered_train_outputs and failure_detail is None and len(predictions) == len(task.train_pairs)

    with timed_section(metrics, "layer5_time_ms"):
        if predictions:
            accuracies = [
                pixel_accuracy(prediction, pair.output or pair.input)
                for prediction, pair in zip(predictions, task.train_pairs)
            ]
            avg_pixel_accuracy = mean(accuracies)
            exact_match = all(accuracy == 1.0 for accuracy in accuracies)
            if selected_hypothesis is not None:
                _, violated = verify_constraints(predictions[0], selected_hypothesis)
                if violated and failure_detail is None:
                    failure_detail = "; ".join(violated)
        else:
            avg_pixel_accuracy = 0.0
            exact_match = False

        failure_type = classify_failure(
            has_perception=bool(train_perception),
            has_hypothesis=has_hypothesis,
            execution_ok=execution_ok,
            exact_match=exact_match,
        )
        if failure_type == "SELECTION_FAIL" and failure_detail is None:
            failure_detail = _selection_failure_detail(train_perception, candidate_sets, hypotheses)
        if failure_type == "ABSTRACTION_FAIL" and failure_detail is None:
            failure_detail = f"best_pixel_accuracy={avg_pixel_accuracy:.4f}"
        if failure_type == "PERCEPTION_FAIL" and failure_detail is None:
            failure_detail = "no_perception_output"
        if failure_type == "EXECUTION_FAIL" and failure_detail is None:
            failure_detail = "execution_error"
        attribution = build_attribution(
            task_id=task.task_id,
            hypothesis=selected_hypothesis,
            success=exact_match,
            pixel_acc=avg_pixel_accuracy,
            failure_type=failure_type,
            failure_detail=failure_detail,
            search_stats=_build_search_stats(
                candidate_sets,
                total_hypothesis_count=len(hypotheses),
                evaluated_hypothesis_count=len(evaluated_hypotheses),
                beam_saturated=beam_saturated,
                metrics=metrics,
            ),
            concept_group=task.concept,
        )

    debug_bundle["attribution"] = to_jsonable(attribution)
    dump_task_debug_bundle(task.task_id, output_dir, debug_bundle)
    return attribution


def _resolve_output_size_rule(hypothesis: Hypothesis) -> str:
    size_rules = [
        predicate.split(":", 1)[1]
        for predicate in hypothesis.constraint_subset["strong"]
        if predicate.startswith("size_rule:")
    ]
    if len(size_rules) != 1:
        raise ValueError("Step 1 requires exactly one strong size_rule:* constraint before execution")
    return size_rules[0]


def _alignment_method(alignment_id: str) -> str:
    return alignment_id.split(":")[1]


def _accumulate_candidate_family(
    family_buckets: dict[tuple[str, str], dict[str, object]],
    plan_id: str,
    alignment: Alignment,
    transforms: list[CandidateTransform],
    constraints: list[CandidateConstraint],
) -> None:
    method_name = _alignment_method(alignment.alignment_id)
    family_key = (plan_id, method_name)
    family_alignment_id = make_alignment_family_id(plan_id, method_name)
    bucket = family_buckets.setdefault(
        family_key,
        {
            "alignment_family_id": family_alignment_id,
            "representative_alignment": alignment,
            "source_alignment_ids": set(),
            "transforms": {},
            "constraints": {},
        },
    )
    bucket["source_alignment_ids"].add(alignment.alignment_id)

    transform_bucket: dict[tuple[str, tuple[str, ...]], dict[str, object]] = bucket["transforms"]  # type: ignore[assignment]
    size_rule_signature = tuple(
        sorted(
            constraint.predicate
            for constraint in constraints
            if constraint.predicate.startswith("size_rule:")
        )
    )
    for transform in transforms:
        program_text = render_program(transform.program) if isinstance(transform.program, Step1Program) else str(transform.program)
        entry = transform_bucket.setdefault(
            (program_text, size_rule_signature),
            {
                "program": transform.program,
                "applicable_pairs": set(),
                "scores": [],
            },
        )
        entry["applicable_pairs"].update(transform.applicable_pairs)
        entry["scores"].append(transform.match_score)

    constraint_bucket: dict[str, set[int]] = bucket["constraints"]  # type: ignore[assignment]
    for constraint in constraints:
        constraint_bucket.setdefault(constraint.predicate, set()).update(constraint.holds_in)


def _materialize_candidate_sets(
    family_buckets: dict[tuple[str, str], dict[str, object]],
) -> tuple[list, list[dict[str, object]]]:
    candidate_sets = []
    layer2_debug: list[dict[str, object]] = []
    for (plan_id, method_name), bucket in sorted(family_buckets.items()):
        family_alignment_id = bucket["alignment_family_id"]
        representative_alignment = bucket["representative_alignment"]
        representative_alignment_id = sorted(bucket["source_alignment_ids"])[0]
        aggregated_alignment = Alignment(
            alignment_id=representative_alignment_id,
            alignment_family_id=family_alignment_id,
            matched_pairs=list(representative_alignment.matched_pairs),
            unmatched_input=list(representative_alignment.unmatched_input),
            unmatched_output=list(representative_alignment.unmatched_output),
            merge_groups=[],
            split_groups=[],
        )

        transforms: list[CandidateTransform] = []
        transform_pairs: set[int] = set()
        for index, ((program_text, _size_rule_signature), entry) in enumerate(sorted(bucket["transforms"].items())):
            applicable_pairs = sorted(entry["applicable_pairs"])
            transform_pairs.update(applicable_pairs)
            scores = entry["scores"]
            transforms.append(
                CandidateTransform(
                    transform_id=make_family_transform_id(family_alignment_id, index),
                    alignment_id=representative_alignment_id,
                    alignment_family_id=family_alignment_id,
                    program=entry["program"],
                    applicable_pairs=applicable_pairs,
                    match_score=sum(scores) / len(scores),
                )
            )

        constraints: list[CandidateConstraint] = []
        constraint_pairs: set[int] = set()
        for index, (predicate, holds_in) in enumerate(sorted(bucket["constraints"].items())):
            sorted_holds = sorted(holds_in)
            constraint_pairs.update(sorted_holds)
            constraints.append(
                CandidateConstraint(
                    constraint_id=make_family_constraint_id(family_alignment_id, index),
                    alignment_id=representative_alignment_id,
                    alignment_family_id=family_alignment_id,
                    predicate=predicate,
                    holds_in=sorted_holds,
                )
            )

        candidate_sets.append(build_candidate_set(plan_id, [aggregated_alignment], transforms, constraints))
        layer2_debug.append(
            {
                "plan_id": plan_id,
                "alignment_id": representative_alignment_id,
                "alignment_family": family_alignment_id,
                "method": method_name,
                "transform_count": len(transforms),
                "constraint_count": len(constraints),
                "covered_pairs": sorted(transform_pairs | constraint_pairs),
            }
        )
    return (candidate_sets, layer2_debug)


def _render_hypotheses_on_train(
    hypotheses: list[Hypothesis],
    train_pairs: list,
    train_perception: list[dict[str, object]],
) -> tuple[dict[str, list[Grid]], dict[str, str]]:
    rendered_outputs: dict[str, list[Grid]] = {}
    render_failures: dict[str, str] = {}
    for hypothesis in hypotheses:
        cache_key = hypothesis_cache_key(hypothesis)
        try:
            output_size_rule = _resolve_output_size_rule(hypothesis)
            program = parse_program(hypothesis.program)
            outputs: list[Grid] = []
            for pair, pair_perception in zip(train_pairs, train_perception):
                plan_lookup = {plan.plan_id: plan for plan in pair_perception["input"].segmentation_plans}
                outputs.append(
                    execute_program(
                        program,
                        plan_lookup[hypothesis.plan_id],
                        pair.input,
                        output_size_rule,
                    )
                )
            rendered_outputs[cache_key] = outputs
        except Exception as exc:
            rendered_outputs[cache_key] = []
            render_failures[cache_key] = str(exc)
    return (rendered_outputs, render_failures)


def _build_search_stats(
    candidate_sets: list,
    total_hypothesis_count: int,
    evaluated_hypothesis_count: int,
    beam_saturated: bool,
    metrics: dict[str, int],
) -> SearchStats:
    return SearchStats(
        candidates_generated=sum(
            len(candidate_set.candidate_transforms) + len(candidate_set.candidate_constraints)
            for candidate_set in candidate_sets
        ),
        candidates_evaluated=evaluated_hypothesis_count,
        search_time_ms=sum(metrics.values()),
        beam_saturated=beam_saturated and total_hypothesis_count > evaluated_hypothesis_count,
        layer1_time_ms=metrics.get("layer1_time_ms", 0),
        layer2_time_ms=metrics.get("layer2_time_ms", 0),
        layer3_time_ms=metrics.get("layer3_time_ms", 0),
        layer4_time_ms=metrics.get("layer4_time_ms", 0),
        layer5_time_ms=metrics.get("layer5_time_ms", 0),
    )


def _selection_failure_detail(
    train_perception: list[dict[str, object]],
    candidate_sets: list,
    hypotheses: list[Hypothesis],
) -> str:
    if not train_perception or any(not item["input"].segmentation_plans for item in train_perception):
        return "PLAN_ERROR"
    if not candidate_sets:
        return "ALIGNMENT_ERROR"
    if all(not candidate_set.candidate_transforms for candidate_set in candidate_sets):
        return "PROGRAM_ERROR"
    if not hypotheses:
        return "CONSTRAINT_SUBSET_ERROR"
    return "PROGRAM_ERROR"


def _plan_diagnostics(perception_output) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for plan in perception_output.segmentation_plans:
        areas = sorted(int(obj.attrs.get("area", 0)) for obj in plan.objects)
        threshold = float(median(areas)) / 4.0 if areas else 0.0
        selected_ids = [obj.id for obj in plan.objects if float(obj.attrs.get("area", 0)) < threshold]
        diagnostics.append(
            {
                "plan_id": plan.plan_id,
                "method": plan.method,
                "bg_color": plan.bg_color,
                "object_count": len(plan.objects),
                "object_areas": areas,
                "noise_objects": {
                    "threshold": threshold,
                    "selected_ids": selected_ids,
                    "selected_count": len(selected_ids),
                },
            }
        )
    return diagnostics
