from __future__ import annotations

from collections import defaultdict

from phase1.src.step2.data.models import CandidateSet, CandidateTransform, Hypothesis
from phase1.src.step2.layer2.constraints import observed_size_rules, partition_constraints
from phase1.src.step2.layer4.dsl import Step1Program, render_program


def assemble_hypotheses(candidate_sets: list[CandidateSet]) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    seen_hypotheses: set[tuple[str, str, str, tuple[str, ...], tuple[str, ...], str]] = set()
    for candidate_set in candidate_sets:
        transforms_by_alignment_family: dict[str, list[CandidateTransform]] = defaultdict(list)
        constraints_by_alignment_family: dict[str, list] = defaultdict(list)

        for transform in candidate_set.candidate_transforms:
            transforms_by_alignment_family[transform.alignment_family_id].append(transform)
        for constraint in candidate_set.candidate_constraints:
            constraints_by_alignment_family[constraint.alignment_family_id].append(constraint)

        for alignment in candidate_set.candidate_alignments:
            alignment_id = alignment.alignment_id
            alignment_family_id = alignment.alignment_family_id
            aligned_transforms = transforms_by_alignment_family.get(alignment_family_id, [])
            aligned_constraints = constraints_by_alignment_family.get(alignment_family_id, [])
            if not aligned_transforms:
                continue
            for transform in aligned_transforms:
                relevant_pairs = sorted(set(transform.applicable_pairs))
                train_pair_count = len(relevant_pairs) or _train_pair_count(aligned_constraints)
                size_rule_variants = observed_size_rules(aligned_constraints, relevant_pairs) or [None]
                program_text = _serialize_program(transform.program)
                for size_rule_variant in size_rule_variants:
                    constraint_subset = partition_constraints(
                        aligned_constraints,
                        train_pair_count,
                        relevant_pairs=relevant_pairs,
                        chosen_size_rule=size_rule_variant,
                    )
                    hypothesis_key = (
                        candidate_set.plan_id,
                        alignment_id,
                        alignment_family_id,
                        tuple(constraint_subset["strong"]),
                        tuple(constraint_subset["weak"]),
                        program_text,
                    )
                    if hypothesis_key in seen_hypotheses:
                        continue
                    seen_hypotheses.add(hypothesis_key)
                    hypotheses.append(
                        Hypothesis(
                            plan_id=candidate_set.plan_id,
                            alignment_id=alignment_id,
                            alignment_family_id=alignment_family_id,
                            constraint_subset={
                                "strong": list(constraint_subset["strong"]),
                                "weak": list(constraint_subset["weak"]),
                            },
                            program=program_text,
                        )
                    )
    return hypotheses


def _train_pair_count(constraints: list) -> int:
    if not constraints:
        return 1
    return max(index for constraint in constraints for index in constraint.holds_in) + 1


def _serialize_program(program: object) -> str:
    if isinstance(program, Step1Program):
        return render_program(program)
    return str(program)
