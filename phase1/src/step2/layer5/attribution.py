from __future__ import annotations

from phase1.src.step2.data.models import Attribution, Hypothesis, SearchStats


def build_attribution(
    task_id: str,
    hypothesis: Hypothesis | None,
    success: bool,
    pixel_acc: float,
    failure_type: str,
    failure_detail: str | None,
    search_stats: SearchStats,
    concept_group: str | None = None,
) -> Attribution:
    if hypothesis is None:
        selected_plan = ""
        selected_alignment = ""
        selected_alignment_family = ""
        selected_program = ""
        selected_constraints = {"strong": [], "weak": []}
    else:
        selected_plan = hypothesis.plan_id
        selected_alignment = hypothesis.alignment_id
        selected_alignment_family = hypothesis.alignment_family_id
        selected_program = hypothesis.program
        selected_constraints = hypothesis.constraint_subset

    return Attribution(
        task_id=task_id,
        eval_mode="A",
        success=success,
        pixel_accuracy=pixel_acc,
        failure_type=failure_type,
        failure_detail=failure_detail,
        selected_plan=selected_plan,
        selected_alignment=selected_alignment,
        selected_alignment_family=selected_alignment_family,
        selected_program=selected_program,
        selected_constraints=selected_constraints,
        search_stats=search_stats,
        concept_group=concept_group,
    )
