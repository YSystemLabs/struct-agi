from __future__ import annotations

import unittest

from phase1.src.step2.data.models import Alignment, CandidateConstraint, CandidateSet, CandidateTransform, Hypothesis
from phase1.src.step2.layer3.hypothesis import assemble_hypotheses
from phase1.src.step2.layer3.scoring import description_length, pre_priority
from phase1.src.step2.layer3.selector import apply_hypothesis_beam, clear_rendered_train_outputs, group_equivalent_hypotheses, hypothesis_cache_key, select_best_hypothesis, set_rendered_train_outputs
from phase1.src.step2.layer4.dsl import PrimitiveCall, Step1Program


class Layer3Tests(unittest.TestCase):
    def test_hypothesis_does_not_mix_alignments(self) -> None:
        candidate_set = CandidateSet(
            plan_id="cc4",
            candidate_alignments=[
                Alignment("cc4:pixel_overlap:0", "cc4:pixel_overlap", [], [], [], [], []),
                Alignment("cc4:bipartite:0", "cc4:bipartite", [], [], [], [], []),
            ],
            candidate_transforms=[
                CandidateTransform("t0", "cc4:pixel_overlap:0", "cc4:pixel_overlap", Step1Program(primitives=(PrimitiveCall("delete"),)), [0], 1.0),
                CandidateTransform("t1", "cc4:bipartite:0", "cc4:bipartite", Step1Program(primitives=(PrimitiveCall("recolor", params={"color": 2}),)), [0], 0.8),
            ],
            candidate_constraints=[
                CandidateConstraint("c0", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "size_rule:preserve_input_size", [0]),
                CandidateConstraint("c1", "cc4:bipartite:0", "cc4:bipartite", "size_rule:fit_transformed_extent", [0]),
            ],
        )
        hypotheses = assemble_hypotheses([candidate_set])
        self.assertEqual({"cc4:pixel_overlap:0", "cc4:bipartite:0"}, {item.alignment_id for item in hypotheses})
        self.assertEqual({"cc4:pixel_overlap", "cc4:bipartite"}, {item.alignment_family_id for item in hypotheses})

    def test_strong_and_weak_constraints_are_preserved(self) -> None:
        candidate_set = CandidateSet(
            plan_id="cc4",
            candidate_alignments=[Alignment("cc4:pixel_overlap:0", "cc4:pixel_overlap", [], [], [], [], [])],
            candidate_transforms=[
                CandidateTransform("t0", "cc4:pixel_overlap:0", "cc4:pixel_overlap", Step1Program(primitives=(PrimitiveCall("delete"),)), [0], 1.0)
            ],
            candidate_constraints=[
                CandidateConstraint("c0", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "size_rule:preserve_input_size", [0]),
                CandidateConstraint("c1", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "relative_position:left_of", [0]),
                CandidateConstraint("c2", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "color_map:1->1", [1]),
            ],
        )
        hypothesis = assemble_hypotheses([candidate_set])[0]
        self.assertIn("strong", hypothesis.constraint_subset)
        self.assertIn("weak", hypothesis.constraint_subset)
        self.assertIn("size_rule:preserve_input_size", hypothesis.constraint_subset["strong"])

    def test_hypothesis_uses_program_scoped_size_rule_slice(self) -> None:
        delete_program = Step1Program(primitives=(PrimitiveCall("delete"),))
        crop_program = Step1Program(primitives=(PrimitiveCall("crop", params={"mode": "tight_bbox"}),))
        candidate_set = CandidateSet(
            plan_id="cc4",
            candidate_alignments=[Alignment("cc4:pixel_overlap:0", "cc4:pixel_overlap", [], [], [], [], [])],
            candidate_transforms=[
                CandidateTransform("t0", "cc4:pixel_overlap:0", "cc4:pixel_overlap", delete_program, [0], 1.0),
                CandidateTransform("t1", "cc4:pixel_overlap:0", "cc4:pixel_overlap", crop_program, [1], 1.0),
            ],
            candidate_constraints=[
                CandidateConstraint("c0", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "size_rule:preserve_input_size", [0]),
                CandidateConstraint("c1", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "size_rule:crop_selected_bbox", [1]),
                CandidateConstraint("c2", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "relative_position:left_of", [0, 1]),
            ],
        )
        hypotheses = assemble_hypotheses([candidate_set])
        by_program = {item.program: item for item in hypotheses}
        self.assertCountEqual(
            ["size_rule:preserve_input_size", "relative_position:left_of"],
            by_program["delete[target=all]"].constraint_subset["strong"],
        )
        self.assertCountEqual(
            ["size_rule:crop_selected_bbox", "relative_position:left_of"],
            by_program["crop[target=all,mode=tight_bbox]"].constraint_subset["strong"],
        )

    def test_same_program_can_branch_into_multiple_size_rule_hypotheses(self) -> None:
        candidate_set = CandidateSet(
            plan_id="cc4",
            candidate_alignments=[Alignment("cc4:pixel_overlap:0", "cc4:pixel_overlap", [], [], [], [], [])],
            candidate_transforms=[
                CandidateTransform(
                    "t0",
                    "cc4:pixel_overlap:0",
                    "cc4:pixel_overlap",
                    Step1Program(primitives=(PrimitiveCall("delete"),)),
                    [0, 1],
                    1.0,
                )
            ],
            candidate_constraints=[
                CandidateConstraint("c0", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "size_rule:preserve_input_size", [0]),
                CandidateConstraint("c1", "cc4:pixel_overlap:0", "cc4:pixel_overlap", "size_rule:crop_selected_bbox", [1]),
            ],
        )
        hypotheses = assemble_hypotheses([candidate_set])
        self.assertEqual(2, len(hypotheses))
        self.assertEqual(
            {
                ("size_rule:crop_selected_bbox",),
                ("size_rule:preserve_input_size",),
            },
            {tuple(item.constraint_subset["strong"]) for item in hypotheses},
        )
        self.assertEqual(2, len({hypothesis_cache_key(item) for item in hypotheses}))

    def test_description_length_counts_program_and_strong_constraints(self) -> None:
        hypothesis = Hypothesis(
            plan_id="cc4",
            alignment_id="cc4:pixel_overlap:0",
            alignment_family_id="cc4:pixel_overlap",
            constraint_subset={"strong": ["size_rule:preserve_input_size"], "weak": []},
            program="translate[target=obj0,dx=2]",
        )
        # §5.3.2: plan(1) + AST nodes(1) + strong(1) + constants("0","2"=2) = 5
        self.assertEqual(5, description_length(hypothesis))
        # attr_ref_ratio = target=(1) / tokens(4) + translate_bonus(0.15) = 0.4
        self.assertEqual((-0.4, 1), pre_priority(hypothesis))

    def test_equivalence_grouping_preserves_members(self) -> None:
        first = Hypothesis("cc4", "a:0", "a", {"strong": ["size_rule:preserve_input_size"], "weak": []}, "p0")
        second = Hypothesis("cc4", "b:0", "b", {"strong": ["size_rule:preserve_input_size"], "weak": []}, "p1")
        groups = group_equivalent_hypotheses(
            [first, second],
            {
                hypothesis_cache_key(first): [[[1]]],
                hypothesis_cache_key(second): [[[1]]],
            },
        )
        self.assertEqual(1, len(groups))
        self.assertEqual(2, len(next(iter(groups.values()))))

    def test_representative_selection_prefers_exact_train_match(self) -> None:
        first = Hypothesis("cc4", "a:0", "a", {"strong": ["size_rule:preserve_input_size"], "weak": []}, "delete[target=all]")
        second = Hypothesis(
            "cc4",
            "b:0",
            "b",
            {"strong": ["size_rule:preserve_input_size", "relative_position:left_of"], "weak": []},
            "recolor[target=all,color=2] ; translate[target=all,dx=1]",
        )
        set_rendered_train_outputs(
            {
                hypothesis_cache_key(first): [[[0]]],
                hypothesis_cache_key(second): [[[1]]],
            }
        )
        try:
            selected, debug = select_best_hypothesis([first, second], [[[1]]], [[[1]]])
        finally:
            clear_rendered_train_outputs()
        self.assertEqual(second.program, selected.program)
        self.assertEqual(2, len(debug["equivalence_classes"]))

    def test_fallback_penalizes_semantic_noop_copy_and_records_reason(self) -> None:
        first = Hypothesis(
            "cc4",
            "a:0",
            "a",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "copy[target=all] ; on_copy: ; on_original:",
        )
        second = Hypothesis(
            "cc4",
            "b:0",
            "b",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "recolor[target=all,color=2] ; translate[target=all,dx=1]",
        )
        set_rendered_train_outputs(
            {
                hypothesis_cache_key(first): [[[0]]],
                hypothesis_cache_key(second): [[[2]]],
            }
        )
        try:
            selected, debug = select_best_hypothesis([first, second], [[[9]]], [[[1]]])
        finally:
            clear_rendered_train_outputs()
        self.assertEqual(second.program, selected.program)
        scored = {entry["program"]: entry for entry in debug["fallback_scores"]}
        self.assertEqual(10, scored[first.program]["heuristic_penalty"])
        self.assertEqual("empty_copy_block", scored[first.program]["penalty_reasons"][0]["reason"])

    def test_hypothesis_beam_uses_pre_priority_and_reports_saturation(self) -> None:
        top = Hypothesis("cc4", "a:0", "a", {"strong": ["size_rule:preserve_input_size"], "weak": []}, "recolor[target=all,color=2]")
        middle = Hypothesis(
            "cc4",
            "b:0",
            "b",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "recolor[target=all,color=2] ; delete[target=all]",
        )
        bottom = Hypothesis("cc4", "c:0", "c", {"strong": ["size_rule:preserve_input_size"], "weak": []}, "rotate[target=all]")
        beam, saturated = apply_hypothesis_beam([bottom, middle, top], beam_size=2)
        self.assertTrue(saturated)
        self.assertEqual([top.program, middle.program], [item.program for item in beam])

    def test_hypothesis_beam_appends_single_extend_to_boundary_keepalive_when_family_missing(self) -> None:
        top = Hypothesis("cc4", "a:0", "a", {"strong": ["size_rule:preserve_input_size"], "weak": []}, "recolor[target=all,color=2]")
        middle = Hypothesis(
            "cc4",
            "b:0",
            "b",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "recolor[target=all,color=2] ; delete[target=all]",
        )
        keepalive = Hypothesis(
            "bg_fg",
            "c:0",
            "c",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "extend_to_boundary[target=center_object,source=full_boundary,direction=vertical_both]",
        )
        beam, saturated = apply_hypothesis_beam([keepalive, middle, top], beam_size=2)
        self.assertTrue(saturated)
        self.assertEqual([top.program, middle.program, keepalive.program], [item.program for item in beam])

    def test_hypothesis_beam_does_not_append_duplicate_extend_to_boundary_keepalive(self) -> None:
        top = Hypothesis(
            "bg_fg",
            "a:0",
            "a",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "extend_to_boundary[target=center_object,source=full_boundary,direction=down]",
        )
        remainder_extend = Hypothesis(
            "bg_fg",
            "b:0",
            "b",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "extend_to_boundary[target=center_object,source=full_boundary,direction=vertical_both]",
        )
        beam, saturated = apply_hypothesis_beam([remainder_extend, top], beam_size=1)
        self.assertTrue(saturated)
        self.assertEqual([top.program], [item.program for item in beam])

    def test_pre_priority_gives_copy_candidate_bonus(self) -> None:
        copy_hypothesis = Hypothesis(
            "cc4",
            "a:0",
            "a",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "copy[target=all] ; on_copy: translate[target=all,dx=1] ; on_original:",
        )
        delete_hypothesis = Hypothesis(
            "cc4",
            "b:0",
            "b",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "delete[target=all]",
        )
        self.assertLess(pre_priority(copy_hypothesis), pre_priority(delete_hypothesis))

    def test_pre_priority_counts_step2_symbolic_params_as_attribute_refs(self) -> None:
        symbolic = Hypothesis(
            "cc4",
            "a:0",
            "a",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "translate[target=all,dx=to_boundary_dx,dy=to_boundary_dy]",
        )
        plain = Hypothesis(
            "cc4",
            "b:0",
            "b",
            {"strong": ["size_rule:preserve_input_size"], "weak": []},
            "translate[target=all,dx=1,dy=0]",
        )
        self.assertLess(pre_priority(symbolic), pre_priority(plain))


if __name__ == "__main__":
    unittest.main()
