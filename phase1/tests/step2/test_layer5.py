from __future__ import annotations

import unittest

from phase1.src.step2.data.models import Hypothesis, SearchStats
from phase1.src.step2.layer5.attribution import build_attribution
from phase1.src.step2.layer5.verify import classify_failure, pixel_accuracy, verify_constraints


class Layer5Tests(unittest.TestCase):
    def test_pixel_accuracy(self) -> None:
        self.assertEqual(0.75, pixel_accuracy([[1, 0], [0, 0]], [[1, 0], [1, 0]]))

    def test_verify_constraints_reports_crop_center_cell_violation(self) -> None:
        hypothesis = Hypothesis(
            plan_id="cc4",
            alignment_id="cc4:pixel_overlap:0",
            alignment_family_id="cc4:pixel_overlap",
            constraint_subset={"strong": ["size_rule:crop_center_cell"], "weak": []},
            program="crop[target=all,mode=center_cell]",
        )
        satisfied, violated = verify_constraints([[1, 0]], hypothesis)
        self.assertEqual([], satisfied)
        self.assertEqual(["size_rule:crop_center_cell"], violated)

    def test_classify_failure(self) -> None:
        self.assertEqual("NONE", classify_failure(True, True, True, True))
        self.assertEqual("PERCEPTION_FAIL", classify_failure(False, True, True, False))
        self.assertEqual("SELECTION_FAIL", classify_failure(True, False, True, False))
        self.assertEqual("EXECUTION_FAIL", classify_failure(True, True, False, False))
        self.assertEqual("ABSTRACTION_FAIL", classify_failure(True, True, True, False))

    def test_build_attribution_keeps_required_fields(self) -> None:
        attribution = build_attribution(
            task_id="Copy1",
            hypothesis=Hypothesis(
                plan_id="cc4",
                alignment_id="cc4:pixel_overlap:0",
                alignment_family_id="cc4:pixel_overlap",
                constraint_subset={"strong": ["size_rule:preserve_input_size"], "weak": []},
                program="delete[target=all]",
            ),
            success=False,
            pixel_acc=0.5,
            failure_type="ABSTRACTION_FAIL",
            failure_detail=None,
            search_stats=SearchStats(1, 1, 1, False, 1, 1, 1, 1, 1),
            concept_group="Copy",
        )
        self.assertEqual("A", attribution.eval_mode)
        self.assertIn("strong", attribution.selected_constraints)
        self.assertEqual("cc4:pixel_overlap", attribution.selected_alignment_family)
        self.assertIsNotNone(attribution.search_stats)
        self.assertEqual("Copy", attribution.concept_group)

    def test_hypothesis_and_attribution_schema_are_stable(self) -> None:
        hypothesis = Hypothesis(
            plan_id="cc4",
            alignment_id="cc4:pixel_overlap:0",
            alignment_family_id="cc4:pixel_overlap",
            constraint_subset={"strong": ["size_rule:preserve_input_size"], "weak": []},
            program="delete[target=all]",
        )
        self.assertEqual(
            {"plan_id", "alignment_id", "alignment_family_id", "constraint_subset", "program"},
            set(hypothesis.to_dict().keys()),
        )

        attribution = build_attribution(
            task_id="Copy1",
            hypothesis=hypothesis,
            success=True,
            pixel_acc=1.0,
            failure_type="NONE",
            failure_detail=None,
            search_stats=SearchStats(1, 1, 1, False, 1, 1, 1, 1, 1),
            concept_group="Copy",
        )
        payload = attribution.to_dict()
        self.assertEqual(
            {
                "task_id",
                "eval_mode",
                "success",
                "pixel_accuracy",
                "failure_type",
                "failure_detail",
                "selected_plan",
                "selected_alignment",
                "selected_alignment_family",
                "selected_program",
                "selected_constraints",
                "search_stats",
                "concept_group",
            },
            set(payload.keys()),
        )
        self.assertEqual(
            {
                "candidates_generated",
                "candidates_evaluated",
                "search_time_ms",
                "beam_saturated",
                "layer1_time_ms",
                "layer2_time_ms",
                "layer3_time_ms",
                "layer4_time_ms",
                "layer5_time_ms",
            },
            set(payload["search_stats"].keys()),
        )


if __name__ == "__main__":
    unittest.main()
