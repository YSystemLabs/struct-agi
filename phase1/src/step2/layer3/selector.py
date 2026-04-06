from __future__ import annotations

from phase1.src.step2.config import STEP2_BEAM_SIZE
from phase1.src.step2.data.models import Grid, Hypothesis
from phase1.src.step2.layer4.dsl import parse_program
from phase1.src.step2.layer3.scoring import description_length, mismatch_sum, pre_priority


_RENDERED_TRAIN_OUTPUTS: dict[str, list[Grid]] = {}
_EMPTY_COPY_BLOCK_PENALTY = 10


def hypothesis_cache_key(hypothesis: Hypothesis) -> str:
    strong = tuple(hypothesis.constraint_subset.get("strong", []))
    weak = tuple(hypothesis.constraint_subset.get("weak", []))
    return (
        f"{hypothesis.plan_id}|{hypothesis.alignment_family_id}|{hypothesis.alignment_id}"
        f"|{repr((strong, weak))}|{hypothesis.program}"
    )


def set_rendered_train_outputs(rendered_train_outputs: dict[str, list[Grid]]) -> None:
    _RENDERED_TRAIN_OUTPUTS.clear()
    _RENDERED_TRAIN_OUTPUTS.update(rendered_train_outputs)


def clear_rendered_train_outputs() -> None:
    _RENDERED_TRAIN_OUTPUTS.clear()


def beam_priority_key(hypothesis: Hypothesis) -> tuple[tuple[float, int], int, str, str, str]:
    return (
        pre_priority(hypothesis),
        description_length(hypothesis),
        hypothesis.program,
        hypothesis.alignment_family_id,
        hypothesis.alignment_id,
    )


def apply_hypothesis_beam(
    hypotheses: list[Hypothesis],
    beam_size: int = STEP2_BEAM_SIZE,
) -> tuple[list[Hypothesis], bool]:
    ranked = sorted(hypotheses, key=beam_priority_key)
    if beam_size <= 0:
        return ([], bool(ranked))
    saturated = len(ranked) > beam_size
    beam = ranked[:beam_size]
    if saturated:
        beam = _append_extend_to_boundary_keepalive(beam, ranked[beam_size:])
    return (beam, saturated)


def group_equivalent_hypotheses(
    hypotheses: list[Hypothesis],
    rendered_train_outputs: dict[str, list[Grid]],
) -> dict[str, list[Hypothesis]]:
    groups: dict[str, list[Hypothesis]] = {}
    for hypothesis in hypotheses:
        outputs = rendered_train_outputs.get(hypothesis_cache_key(hypothesis), [])
        key = repr(outputs)
        groups.setdefault(key, []).append(hypothesis)
    return groups


def select_best_hypothesis(
    hypotheses: list[Hypothesis],
    train_inputs: list[Grid],
    train_outputs: list[Grid],
) -> tuple[Hypothesis, dict]:
    if not hypotheses:
        raise ValueError("Cannot select a hypothesis from an empty list")

    rendered_train_outputs = dict(_RENDERED_TRAIN_OUTPUTS)
    groups = group_equivalent_hypotheses(hypotheses, rendered_train_outputs)
    representatives: list[Hypothesis] = []
    equivalence_classes: list[dict] = []
    fallback_scores: list[dict] = []
    for class_key, members in sorted(groups.items()):
        representative = min(
            members,
            key=lambda item: (description_length(item), pre_priority(item), item.program),
        )
        representatives.append(representative)
        equivalence_classes.append(
            {
                "class_key": class_key,
                "members": [hypothesis.program for hypothesis in members],
                "class_size": len(members),
                "representative_program": representative.program,
                "representative_constraints": representative.constraint_subset,
            }
        )
        mismatch = mismatch_sum(rendered_train_outputs.get(hypothesis_cache_key(representative), []), train_outputs)
        heuristic_penalty, penalty_reasons = _fallback_penalty(representative)
        fallback_scores.append(
            {
                "program": representative.program,
                "alignment_id": representative.alignment_id,
                "alignment_family_id": representative.alignment_family_id,
                "mismatch_sum": mismatch,
                "description_length": description_length(representative),
                "heuristic_penalty": heuristic_penalty,
                "penalty_reasons": penalty_reasons,
                "fallback_primary_score": mismatch + 1.0 * description_length(representative) + heuristic_penalty,
            }
        )

    exact_matches = [
        hypothesis
        for hypothesis in representatives
        if rendered_train_outputs.get(hypothesis_cache_key(hypothesis), []) == train_outputs
    ]
    if exact_matches:
        best = min(
            exact_matches,
            key=lambda item: (description_length(item), pre_priority(item), item.program),
        )
    else:
        best = min(
            representatives,
            key=lambda item: (
                mismatch_sum(rendered_train_outputs.get(hypothesis_cache_key(item), []), train_outputs)
                + 1.0 * description_length(item)
                + _fallback_penalty(item)[0],
                pre_priority(item),
                item.program,
            ),
        )

    debug = {
        "equivalence_classes": equivalence_classes,
        "selected_program": best.program,
        "selected_alignment": best.alignment_id,
        "selected_alignment_family": best.alignment_family_id,
        "selected_plan": best.plan_id,
        "used_fallback": not bool(exact_matches),
        "fallback_scores": fallback_scores,
    }
    return (best, debug)


def _fallback_penalty(hypothesis: Hypothesis) -> tuple[int, list[dict[str, int | str]]]:
    if _is_semantic_noop_copy(hypothesis.program):
        return (
            _EMPTY_COPY_BLOCK_PENALTY,
            [{"reason": "empty_copy_block", "penalty": _EMPTY_COPY_BLOCK_PENALTY}],
        )
    return (0, [])


def _is_semantic_noop_copy(program_text: str) -> bool:
    try:
        program = parse_program(program_text)
    except Exception:
        return False
    if program.copy_block is None or program.primitives:
        return False
    return not program.copy_block.on_copy.primitives and not program.copy_block.on_original.primitives


def _append_extend_to_boundary_keepalive(
    beam: list[Hypothesis],
    remainder: list[Hypothesis],
) -> list[Hypothesis]:
    if any(_program_contains_primitive(item.program, "extend_to_boundary") for item in beam):
        return beam
    keepalive = next(
        (item for item in remainder if _program_contains_primitive(item.program, "extend_to_boundary")),
        None,
    )
    if keepalive is None:
        return beam
    return [*beam, keepalive]


def _program_contains_primitive(program_text: str, primitive_name: str) -> bool:
    try:
        program = parse_program(program_text)
    except Exception:
        return False
    if any(primitive.op == primitive_name for primitive in program.primitives):
        return True
    if program.copy_block is None:
        return False
    return any(primitive.op == primitive_name for primitive in program.copy_block.on_copy.primitives) or any(
        primitive.op == primitive_name for primitive in program.copy_block.on_original.primitives
    )
