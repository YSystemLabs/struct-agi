from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from phase1.src.step2.data.models import Alignment, CandidateConstraint, CandidateTransform, SearchStats
from phase1.src.step2.data.loader import load_step2_train_tasks
from phase1.src.step2.layer4.dsl import PrimitiveCall, Step1Program
from phase1.src.step2.runner.batch_runner import build_summary, run_step2_batch
from phase1.src.step2.runner.task_runner import _build_search_stats, _materialize_candidate_sets, run_task


class RunnerTests(unittest.TestCase):
    def test_single_task_run_writes_debug_artifacts(self) -> None:
        task = load_step2_train_tasks()[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            attribution = run_task(task, temp_dir)
            debug_dir = Path(temp_dir) / "debug" / task.task_id
            self.assertTrue((debug_dir / "layer1.json").exists())
            self.assertTrue((debug_dir / "layer2.json").exists())
            self.assertTrue((debug_dir / "selected_hypothesis.json").exists())
            self.assertTrue((debug_dir / "attribution.json").exists())
            self.assertEqual(task.task_id, attribution.task_id)

    def test_batch_runner_only_consumes_train_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            attributions = run_step2_batch(temp_dir)
            self.assertEqual(36, len(attributions))
            self.assertEqual(
                {"Copy", "Center", "MoveToBoundary", "ExtendToBoundary", "ExtractObjects", "CleanUp"},
                {item.concept_group for item in attributions},
            )

    def test_summary_contains_required_statistics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            attributions = run_step2_batch(temp_dir)
            summary = build_summary(attributions)
            self.assertIn("exact_solved", summary)
            self.assertIn("failure_type_distribution", summary)
            self.assertIn("average_layer_times_ms", summary)
            self.assertIn("most_selected_plan", summary)
            self.assertIn("most_selected_alignment_strategy", summary)

    def test_family_materialization_uses_family_scoped_candidate_ids(self) -> None:
        family_buckets = {
            ("cc4", "pixel_overlap"): {
                "alignment_family_id": "cc4:pixel_overlap",
                "representative_alignment": Alignment("cc4:pixel_overlap:0", "cc4:pixel_overlap", [], [], [], [], []),
                "source_alignment_ids": {"cc4:pixel_overlap:0", "cc4:pixel_overlap:1"},
                "transforms": {
                    ("delete[target=all]", ("size_rule:preserve_input_size",)): {
                        "program": Step1Program(primitives=(PrimitiveCall("delete"),)),
                        "applicable_pairs": {0, 1},
                        "scores": [1.0, 1.0],
                    }
                },
                "constraints": {
                    "size_rule:preserve_input_size": {0, 1},
                },
            }
        }
        candidate_sets, _ = _materialize_candidate_sets(family_buckets)
        transform = candidate_sets[0].candidate_transforms[0]
        constraint = candidate_sets[0].candidate_constraints[0]
        self.assertTrue(transform.transform_id.startswith("cc4:pixel_overlap:transform:"))
        self.assertTrue(constraint.constraint_id.startswith("cc4:pixel_overlap:constraint:"))
        self.assertEqual("cc4:pixel_overlap:0", transform.alignment_id)
        self.assertEqual("cc4:pixel_overlap", transform.alignment_family_id)

    def test_search_stats_marks_beam_saturation_when_hypotheses_are_truncated(self) -> None:
        stats = _build_search_stats([], total_hypothesis_count=40, evaluated_hypothesis_count=32, beam_saturated=True, metrics={})
        self.assertEqual(SearchStats(0, 32, 0, True, 0, 0, 0, 0, 0), stats)


if __name__ == "__main__":
    unittest.main()
