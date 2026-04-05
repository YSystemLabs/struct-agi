from __future__ import annotations

import unittest

from phase1.src.step2.layer1.objects import build_object, build_whole_grid_object, extract_cc_objects
from phase1.src.step2.layer1.perception import build_segmentation_plan, perceive_grid
from phase1.src.step2.layer1.relations import extract_relations
from phase1.tests.step2.fixtures import diag_touch_grid


class Layer1Tests(unittest.TestCase):
    def test_cc4_segmentation_splits_diagonal_touch(self) -> None:
        components = extract_cc_objects(diag_touch_grid, 4)
        self.assertEqual(2, len(components))

    def test_cc8_segmentation_merges_diagonal_touch(self) -> None:
        components = extract_cc_objects(diag_touch_grid, 8)
        self.assertEqual(1, len(components))

    def test_whole_grid_segmentation_always_has_one_object(self) -> None:
        plan = build_segmentation_plan([[1, 0], [0, 2]], "whole_grid")
        self.assertEqual(1, len(plan.objects))
        self.assertEqual("whole_grid", plan.plan_id)

    def test_build_object_populates_bbox_and_centers(self) -> None:
        grid = [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        obj = build_object("cc4:0", {(0, 0), (0, 1), (1, 1)}, grid)
        self.assertEqual((0, 0, 1, 1), obj.bbox)
        self.assertEqual(3, obj.attrs["area"])
        self.assertEqual(2, obj.attrs["width"])
        self.assertEqual(2, obj.attrs["height"])
        self.assertEqual(0.5, obj.attrs["center_row"])
        self.assertEqual(0.5, obj.attrs["center_col"])

    def test_layer1_object_schema_is_stable(self) -> None:
        grid = [[1, 1, 0], [0, 1, 0], [0, 0, 0]]
        obj = build_object("cc4:0", {(0, 0), (0, 1), (1, 1)}, grid)
        self.assertEqual(
            {
                "dominant_color",
                "color",
                "area",
                "height",
                "width",
                "center_row",
                "center_col",
                "canvas_height",
                "canvas_width",
            },
            set(obj.attrs.keys()),
        )
        self.assertEqual([0, 0, 1, 1], obj.to_dict()["bbox"])

    def test_perception_output_schema_is_stable(self) -> None:
        output = perceive_grid([[1, 0], [0, 1]])
        payload = output.to_dict()
        self.assertEqual({"segmentation_plans"}, set(payload.keys()))
        first_plan = payload["segmentation_plans"][0]
        self.assertEqual({"plan_id", "method", "objects", "relations", "bg_color"}, set(first_plan.keys()))
        first_object = first_plan["objects"][0]
        self.assertEqual({"id", "pixels", "bbox", "attrs", "pixel_colors"}, set(first_object.keys()))

    def test_extract_relations_only_outputs_relative_and_alignment(self) -> None:
        grid = [[1, 1, 0, 2, 2], [0, 0, 0, 0, 0]]
        left = build_object("a", {(0, 0), (0, 1)}, grid)
        right = build_object("b", {(0, 3), (0, 4)}, grid)
        relations = extract_relations([left, right])
        self.assertIn(("a", "b", "left_of"), relations)
        self.assertIn(("a", "b", "aligned_top"), relations)
        self.assertIn(("a", "b", "aligned_bottom"), relations)
        self.assertIn(("a", "b", "aligned_row_center"), relations)
        self.assertTrue(all(relation[2].startswith(("aligned_", "left_of", "right_of", "above", "below")) for relation in relations))

    def test_perceive_grid_returns_four_stable_plans(self) -> None:
        output = perceive_grid([[1, 0], [0, 1]])
        self.assertEqual(["cc4", "cc8", "whole_grid", "bg_fg"], [plan.plan_id for plan in output.segmentation_plans])

    def test_bg_fg_segmentation_uses_most_frequent_color_as_background(self) -> None:
        output = perceive_grid([[2, 2, 2], [2, 1, 0], [2, 0, 0]])
        bg_fg_plan = next(plan for plan in output.segmentation_plans if plan.plan_id == "bg_fg")
        self.assertEqual(2, bg_fg_plan.bg_color)
        self.assertEqual(1, len(bg_fg_plan.objects))

    def test_build_whole_grid_object_uses_canvas_bbox(self) -> None:
        obj = build_whole_grid_object([[0, 1, 0], [2, 0, 0]])
        self.assertEqual((0, 0, 1, 2), obj.bbox)
        self.assertEqual(6, obj.attrs["area"])


if __name__ == "__main__":
    unittest.main()
