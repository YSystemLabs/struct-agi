from __future__ import annotations

import unittest

from phase1.src.step2.config import STEP2_DIAGNOSTIC_TASKS, STEP2_TRAIN_TASKS
from phase1.src.step2.data.loader import load_step2_task_ids, load_step2_train_tasks, load_task


class LoaderTests(unittest.TestCase):
    def test_load_step2_train_tasks_returns_36_tasks(self) -> None:
        tasks = load_step2_train_tasks()
        self.assertEqual(36, len(tasks))

    def test_diagnostic_tasks_are_not_in_default_load_list(self) -> None:
        train_ids = set(load_step2_task_ids())
        diagnostic_ids = {task_id for _, task_id, _ in STEP2_DIAGNOSTIC_TASKS}
        self.assertTrue(diagnostic_ids.isdisjoint(train_ids))
        self.assertEqual(36, len(STEP2_TRAIN_TASKS))

    def test_copy1_and_center1_pair_counts_are_parsed(self) -> None:
        copy_task = load_task(*STEP2_TRAIN_TASKS[0])
        center_task = load_task(*STEP2_TRAIN_TASKS[6])
        self.assertEqual("Copy1", copy_task.task_id)
        self.assertEqual(3, len(copy_task.train_pairs))
        self.assertEqual(3, len(copy_task.test_pairs))
        self.assertEqual("Center1", center_task.task_id)
        self.assertGreaterEqual(len(center_task.train_pairs), 1)
        self.assertGreaterEqual(len(center_task.test_pairs), 1)
        self.assertTrue(all(pair.split == "train" for pair in copy_task.train_pairs))
        self.assertTrue(all(pair.split == "test" for pair in copy_task.test_pairs))


if __name__ == "__main__":
    unittest.main()
