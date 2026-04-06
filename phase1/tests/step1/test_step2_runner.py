from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phase1.src.step2.data.loader import load_step2_train_tasks
from phase1.src.step2.data.models import ArcTask, Attribution, ExamplePair, SearchStats
from phase1.src.step2.runner.batch_runner import build_regression_flags, build_summary, run_step2_batch
from phase1.src.step2.runner.task_runner import run_task


def _fake_task(task_id: str, concept: str) -> ArcTask:
    pair = ExamplePair(pair_index=0, split="train", input=[[0]], output=[[0]])
    return ArcTask(task_id=task_id, concept=concept, file_path=f"{task_id}.json", train_pairs=[pair], test_pairs=[])


def _fake_attr(task_id: str, concept: str, success: bool) -> Attribution:
    return Attribution(
        task_id=task_id,
        eval_mode="A",
        success=success,
        pixel_accuracy=1.0 if success else 0.25,
        failure_type="NONE" if success else "ABSTRACTION_FAIL",
        failure_detail=None if success else "best_pixel_accuracy=0.2500",
        selected_plan="bg_fg",
        selected_alignment="bg_fg:pixel_overlap:0",
        selected_alignment_family="bg_fg:pixel_overlap",
        selected_program="crop[target=largest_object,mode=tight_bbox]",
        selected_constraints={"strong": ["size_rule:crop_selected_bbox"], "weak": []},
        search_stats=SearchStats(1, 1, 1, False, 1, 1, 1, 1, 1),
        concept_group=concept,
    )


class Step2RunnerTests(unittest.TestCase):
    def test_batch_runner_supports_stage_and_group_filters(self) -> None:
        tasks = [
            _fake_task("Copy1", "Copy"),
            _fake_task("Center1", "Center"),
            _fake_task("MoveToBoundary1", "MoveToBoundary"),
            _fake_task("CleanUp1", "CleanUp"),
        ]

        with patch("phase1.src.step2.runner.batch_runner.load_step2_train_tasks", return_value=tasks):
            with patch(
                "phase1.src.step2.runner.batch_runner.run_task",
                side_effect=lambda task, _output_dir: _fake_attr(task.task_id, task.concept, True),
            ):
                attributions_2a = run_step2_batch("/tmp/unused", stage="2a")
                self.assertEqual(["Copy1", "Center1"], [item.task_id for item in attributions_2a])

                move_only = run_step2_batch("/tmp/unused", stage="2b", group="MoveToBoundary")
                self.assertEqual(["MoveToBoundary1"], [item.task_id for item in move_only])

    def test_summary_contains_phase8_fields(self) -> None:
        attributions = [
            _fake_attr("Copy1", "Copy", False),
            _fake_attr("Copy2", "Copy", True),
            _fake_attr("MoveToBoundary1", "MoveToBoundary", True),
        ]

        summary = build_summary(attributions)
        regression_flags = build_regression_flags(attributions)

        self.assertIn("concept_group_summary", summary)
        self.assertIn("regression_flag_distribution", summary)
        self.assertIn("regression_tasks", summary)
        self.assertIn("Copy", summary["concept_group_summary"])
        self.assertEqual(1, summary["concept_group_summary"]["Copy"]["exact_solved"])
        self.assertEqual(["step2a_exact_regression"], regression_flags["Copy1"])
        self.assertEqual(1, summary["regression_flag_distribution"]["step2a_exact_regression"])
        self.assertIn("CleanUp", summary["frozen_unresolved_groups"])

    def test_single_task_run_writes_phase8_diagnostics(self) -> None:
        task = load_step2_train_tasks()[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            attribution = run_task(task, temp_dir)
            debug_dir = Path(temp_dir) / "debug" / task.task_id
            diagnostics_path = debug_dir / "diagnostics.json"
            self.assertTrue(diagnostics_path.exists())
            payload = json.loads(diagnostics_path.read_text(encoding="utf-8"))
            self.assertTrue(payload)
            self.assertIn("input_plans", payload[0])
            bg_fg_plan = next(item for item in payload[0]["input_plans"] if item["plan_id"] == "bg_fg")
            self.assertIn("bg_color", bg_fg_plan)
            self.assertIn("noise_objects", bg_fg_plan)
            self.assertEqual(task.task_id, attribution.task_id)


if __name__ == "__main__":
    unittest.main()