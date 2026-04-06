from __future__ import annotations

import unittest

from phase1.src.step2.data.models import Alignment, ObjectData, SegmentationPlan
from phase1.src.step2.layer1.perception import build_segmentation_plan
from phase1.src.step2.layer2.alignment import align_objects
from phase1.src.step2.layer2.constraints import extract_constraints, partition_constraints
from phase1.src.step2.layer2.diff import classify_alignment_diffs, classify_object_diff
from phase1.src.step2.layer2.sketches import build_candidate_set, generate_candidate_transforms
from phase1.src.step2.layer4.dsl import render_program


def _obj(object_id: str, pixels: set[tuple[int, int]], color: int) -> ObjectData:
    rows = [row for row, _ in pixels]
    cols = [col for _, col in pixels]
    return ObjectData(
        id=object_id,
        pixels=pixels,
        bbox=(min(rows), min(cols), max(rows), max(cols)),
        attrs={
            "dominant_color": color,
            "color": color,
            "area": len(pixels),
            "height": max(rows) - min(rows) + 1,
            "width": max(cols) - min(cols) + 1,
            "center_row": (min(rows) + max(rows)) / 2,
            "center_col": (min(cols) + max(cols)) / 2,
        },
    )


def _plan(plan_id: str, objects: list[ObjectData], relations: list[tuple[str, str, str]] | None = None) -> SegmentationPlan:
    return SegmentationPlan(plan_id=plan_id, method=plan_id, objects=objects, relations=relations or [])


class Layer2Tests(unittest.TestCase):
    def test_pixel_overlap_matching_has_priority(self) -> None:
        input_plan = _plan("cc4", [_obj("in0", {(0, 0)}, 1)])
        output_plan = _plan("cc4", [_obj("out0", {(0, 0)}, 1)])
        alignments = align_objects(input_plan, output_plan, 0)
        self.assertEqual("cc4:pixel_overlap:0", alignments[0].alignment_id)

    def test_color_shape_matching_is_used_when_no_overlap(self) -> None:
        input_plan = _plan("cc4", [_obj("in0", {(0, 0), (0, 1)}, 2)])
        output_plan = _plan("cc4", [_obj("out0", {(2, 2), (2, 3)}, 2)])
        alignments = align_objects(input_plan, output_plan, 1)
        self.assertEqual("cc4:color_shape:1", alignments[0].alignment_id)

    def test_optimal_bipartite_matching_is_used_as_last_resort(self) -> None:
        input_plan = _plan("cc4", [_obj("in0", {(0, 0)}, 1), _obj("in1", {(4, 4)}, 2)])
        output_plan = _plan("cc4", [_obj("out0", {(1, 0)}, 9), _obj("out1", {(5, 4)}, 8)])
        alignments = align_objects(input_plan, output_plan, 2)
        self.assertEqual("cc4:bipartite:2", alignments[-1].alignment_id)
        self.assertEqual(2, len(alignments[-1].matched_pairs))

    def test_all_fail_returns_empty_list(self) -> None:
        self.assertEqual([], align_objects(_plan("cc4", []), _plan("cc4", []), 3))

    def test_alignment_id_is_preserved_in_transforms_and_constraints(self) -> None:
        input_obj = _obj("in0", {(0, 0)}, 3)
        output_obj = _obj("out0", {(0, 1)}, 3)
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj], relations=[("out0", "out0", "aligned_row_center")])
        alignment = align_objects(input_plan, output_plan, 4)[-1]
        transforms = generate_candidate_transforms(input_plan, output_plan, alignment, 4)
        constraints = extract_constraints(input_plan, output_plan, alignment, 4)
        self.assertTrue(all(item.alignment_id == alignment.alignment_id for item in transforms))
        self.assertTrue(all(item.alignment_id == alignment.alignment_id for item in constraints))
        self.assertTrue(all(item.alignment_family_id == alignment.alignment_family_id for item in transforms))
        self.assertTrue(all(item.alignment_family_id == alignment.alignment_family_id for item in constraints))
        self.assertTrue(all(item.transform_id.startswith(f"{alignment.alignment_id}:transform:") for item in transforms))
        self.assertTrue(all(item.constraint_id.startswith(f"{alignment.alignment_id}:constraint:") for item in constraints))

    def test_diff_and_partition_constraints_are_step1_bounded(self) -> None:
        input_obj = _obj("in0", {(0, 0), (0, 1), (1, 0)}, 5)
        output_obj = _obj("out0", {(0, 0), (0, 1), (1, 0), (1, 1)}, 5)
        self.assertEqual("fill", classify_object_diff(input_obj, output_obj))
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 5)[-1]
        constraints = extract_constraints(input_plan, output_plan, alignment, 5)
        partitioned = partition_constraints(constraints, 1)
        self.assertEqual(1, sum(1 for item in partitioned["strong"] if item.startswith("size_rule:")))

    def test_build_candidate_set_collects_outputs(self) -> None:
        input_obj = _obj("in0", {(0, 0)}, 1)
        output_obj = _obj("out0", {(0, 0)}, 1)
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[0]
        transforms = generate_candidate_transforms(input_plan, output_plan, alignment, 0)
        constraints = extract_constraints(input_plan, output_plan, alignment, 0)
        candidate_set = build_candidate_set(input_plan.plan_id, [alignment], transforms, constraints)
        self.assertEqual("cc4", candidate_set.plan_id)
        self.assertEqual(1, len(candidate_set.candidate_alignments))
        self.assertEqual(["copy"], classify_alignment_diffs(input_plan, output_plan, alignment))

    def test_size_rule_uses_canvas_shape_not_object_bbox(self) -> None:
        input_plan = build_segmentation_plan([[1, 1, 0], [1, 0, 0], [0, 0, 0]], "cc4")
        output_plan = build_segmentation_plan([[1, 0, 0], [0, 0, 0], [0, 0, 0]], "cc4")
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        constraints = extract_constraints(input_plan, output_plan, alignment, 0)
        self.assertIn("size_rule:preserve_input_size", [item.predicate for item in constraints])

    def test_translate_diff_generates_copy_then_translate_candidate(self) -> None:
        input_obj = _obj("in0", {(0, 0), (0, 1)}, 4)
        output_obj = _obj("out0", {(0, 2), (0, 3)}, 4)
        input_obj.attrs["canvas_height"] = 1
        input_obj.attrs["canvas_width"] = 2
        output_obj.attrs["canvas_height"] = 1
        output_obj.attrs["canvas_width"] = 4
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("copy[target=in0] ; on_copy: translate[target=all,dx=2,dy=0] ; on_original:", programs)
        self.assertIn("copy[target=all] ; on_copy: translate[target=all,dx=2,dy=0] ; on_original:", programs)
        self.assertIn("copy[target=all] ; on_copy: translate[target=all,dx=input_width,dy=0] ; on_original:", programs)

    def test_fill_diff_generates_center_cell_fill_candidate(self) -> None:
        input_obj = _obj("in0", {(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)}, 7)
        output_obj = _obj("out0", {(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)}, 7)
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("fill[target=all,mode=center_cell]", programs)
        self.assertIn("fill[target=in0,mode=center_cell]", programs)

    def test_translate_diff_generates_symbolic_input_height_candidate(self) -> None:
        input_obj = _obj("in0", {(0, 0), (1, 0)}, 5)
        output_obj = _obj("out0", {(2, 0), (3, 0)}, 5)
        input_obj.attrs["canvas_height"] = 2
        input_obj.attrs["canvas_width"] = 1
        output_obj.attrs["canvas_height"] = 4
        output_obj.attrs["canvas_width"] = 1
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("copy[target=all] ; on_copy: translate[target=all,dx=0,dy=input_height] ; on_original:", programs)

    def test_bg_fg_translate_diff_generates_largest_object_candidate(self) -> None:
        large = _obj("large", {(0, 0), (0, 1), (1, 0), (1, 1)}, 5)
        large.attrs["canvas_height"] = 5
        large.attrs["canvas_width"] = 5
        small = _obj("small", {(4, 4)}, 9)
        small.attrs["canvas_height"] = 5
        small.attrs["canvas_width"] = 5
        moved_large = _obj("out0", {(1, 1), (1, 2), (2, 1), (2, 2)}, 5)
        moved_large.attrs["canvas_height"] = 5
        moved_large.attrs["canvas_width"] = 5
        input_plan = _plan("bg_fg", [large, small])
        output_plan = _plan("bg_fg", [moved_large])
        alignment = Alignment("bg_fg:bipartite:0", "bg_fg:bipartite", [("large", "out0", 1.0)], ["small"], [], [], [])
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("translate[target=largest_object,dx=1,dy=1]", programs)

    def test_boundary_translate_diff_is_classified_and_generates_boundary_symbol(self) -> None:
        input_obj = _obj("in0", {(1, 1), (2, 1), (2, 2)}, 4)
        input_obj.attrs["canvas_height"] = 5
        input_obj.attrs["canvas_width"] = 5
        output_obj = _obj("out0", {(1, 3), (2, 3), (2, 4)}, 4)
        output_obj.attrs["canvas_height"] = 5
        output_obj.attrs["canvas_width"] = 5
        self.assertEqual("boundary_translate", classify_object_diff(input_obj, output_obj))
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("translate[target=in0,dx=to_boundary_dx,dy=to_boundary_dy]", programs)
        self.assertIn("translate[target=all,dx=to_boundary_dx,dy=to_boundary_dy]", programs)

    def test_translate_diff_generates_nearest_object_symbol(self) -> None:
        mover = _obj("mover", {(0, 0)}, 5)
        mover.attrs["canvas_height"] = 5
        mover.attrs["canvas_width"] = 5
        near = _obj("near", {(0, 4)}, 2)
        near.attrs["canvas_height"] = 5
        near.attrs["canvas_width"] = 5
        far = _obj("far", {(4, 2)}, 9)
        far.attrs["canvas_height"] = 5
        far.attrs["canvas_width"] = 5
        output_obj = _obj("out0", {(0, 3)}, 5)
        output_obj.attrs["canvas_height"] = 5
        output_obj.attrs["canvas_width"] = 5
        input_plan = _plan("cc4", [mover, near, far])
        output_plan = _plan("cc4", [output_obj, near, far])
        alignment = Alignment(
            "cc4:bipartite:0",
            "cc4:bipartite",
            [("mover", "out0", 1.0), ("near", "near", 1.0), ("far", "far", 1.0)],
            [],
            [],
            [],
            [],
        )
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("translate[target=mover,dx=to_nearest_object_dx,dy=to_nearest_object_dy]", programs)
        self.assertIn("translate[target=all,dx=to_nearest_object_dx,dy=to_nearest_object_dy]", programs)

    def test_extend_to_boundary_diff_is_classified_and_generates_directional_candidate(self) -> None:
        input_obj = _obj("in0", {(1, 1)}, 3)
        input_obj.attrs["canvas_height"] = 3
        input_obj.attrs["canvas_width"] = 4
        output_obj = _obj("out0", {(1, 1), (1, 2), (1, 3)}, 3)
        output_obj.attrs["canvas_height"] = 3
        output_obj.attrs["canvas_width"] = 4
        self.assertEqual("extend_to_boundary", classify_object_diff(input_obj, output_obj, [input_obj]))
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("extend_to_boundary[target=in0,direction=right,source=full_boundary]", programs)

    def test_extend_to_boundary_diff_generates_nearest_boundary_when_tie_break_matches(self) -> None:
        input_obj = _obj("in0", {(1, 1)}, 8)
        input_obj.attrs["canvas_height"] = 3
        input_obj.attrs["canvas_width"] = 3
        output_obj = _obj("out0", {(0, 1), (1, 1)}, 8)
        output_obj.attrs["canvas_height"] = 3
        output_obj.attrs["canvas_width"] = 3
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("extend_to_boundary[target=in0,direction=nearest_boundary,source=full_boundary]", programs)

    def test_extend_to_boundary_diff_generates_nearest_object_boundary_candidate(self) -> None:
        mover = _obj("mover", {(2, 1)}, 4)
        mover.attrs["canvas_height"] = 5
        mover.attrs["canvas_width"] = 6
        blocker = _obj("blocker", {(2, 4)}, 9)
        blocker.attrs["canvas_height"] = 5
        blocker.attrs["canvas_width"] = 6
        output_obj = _obj("out0", {(2, 1), (2, 2), (2, 3)}, 4)
        output_obj.attrs["canvas_height"] = 5
        output_obj.attrs["canvas_width"] = 6
        input_plan = _plan("cc4", [mover, blocker])
        output_plan = _plan("cc4", [output_obj, blocker])
        alignment = Alignment(
            "cc4:bipartite:0",
            "cc4:bipartite",
            [("mover", "out0", 1.0), ("blocker", "blocker", 1.0)],
            [],
            [],
            [],
            [],
        )
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("extend_to_boundary[target=mover,direction=to_nearest_object_boundary,source=full_boundary]", programs)

    def test_extend_to_boundary_diff_generates_horizontal_both_candidate(self) -> None:
        input_obj = _obj("in0", {(1, 2)}, 6)
        input_obj.attrs["canvas_height"] = 3
        input_obj.attrs["canvas_width"] = 5
        output_obj = _obj("out0", {(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)}, 6)
        output_obj.attrs["canvas_height"] = 3
        output_obj.attrs["canvas_width"] = 5
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("extend_to_boundary[target=in0,direction=horizontal_both,source=full_boundary]", programs)

    def test_extend_to_boundary_diff_generates_center_row_source_candidate(self) -> None:
        input_obj = _obj("in0", {(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3)}, 5)
        input_obj.attrs["canvas_height"] = 5
        input_obj.attrs["canvas_width"] = 6
        output_obj = _obj("out0", {(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3), (2, 4), (2, 5)}, 5)
        output_obj.attrs["canvas_height"] = 5
        output_obj.attrs["canvas_width"] = 6
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = align_objects(input_plan, output_plan, 0)[-1]
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("extend_to_boundary[target=in0,direction=right,source=center_row]", programs)

    def test_extend_to_boundary_diff_generates_gap_thinner_object_candidate(self) -> None:
        bar = _obj("bar", {(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)}, 1)
        bar.attrs["canvas_height"] = 6
        bar.attrs["canvas_width"] = 6
        stem = _obj("stem", {(3, 3), (4, 3), (5, 3)}, 2)
        stem.attrs["canvas_height"] = 6
        stem.attrs["canvas_width"] = 6
        out_stem = _obj("out_stem", {(2, 3), (3, 3), (4, 3), (5, 3)}, 2)
        out_stem.attrs["canvas_height"] = 6
        out_stem.attrs["canvas_width"] = 6
        input_plan = _plan("bg_fg", [bar, stem], relations=[("bar", "stem", "above"), ("stem", "bar", "below")])
        output_plan = _plan("bg_fg", [bar, out_stem], relations=[("bar", "out_stem", "above"), ("out_stem", "bar", "below")])
        alignment = Alignment(
            "bg_fg:bipartite:0",
            "bg_fg:bipartite",
            [("stem", "out_stem", 1.0), ("bar", "bar", 1.0)],
            [],
            [],
            [],
            [],
        )
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn(
            "extend_to_boundary[target=gap_thinner_object,direction=to_nearest_object_boundary,source=center_col]",
            programs,
        )

    def test_crop_diff_generates_center_object_selector_candidate(self) -> None:
        frame = _obj("frame", {(0, 0), (0, 6), (6, 0), (6, 6)}, 1)
        frame.attrs["canvas_height"] = 7
        frame.attrs["canvas_width"] = 7
        center = _obj("center", {(2, 2), (2, 3), (3, 2), (3, 3)}, 2)
        center.attrs["canvas_height"] = 7
        center.attrs["canvas_width"] = 7
        output_obj = _obj("out0", {(0, 0), (0, 1), (1, 0), (1, 1)}, 2)
        output_obj.attrs["canvas_height"] = 2
        output_obj.attrs["canvas_width"] = 2
        input_plan = _plan("cc4", [frame, center])
        output_plan = _plan("cc4", [output_obj])
        alignment = Alignment("cc4:bipartite:0", "cc4:bipartite", [("center", "out0", 1.0)], ["frame"], [], [], [])
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("crop[target=center_object,mode=tight_bbox]", programs)

    def test_unmatched_center_object_generates_delete_selector_candidate(self) -> None:
        left = _obj("left", {(0, 0)}, 1)
        left.attrs["canvas_height"] = 3
        left.attrs["canvas_width"] = 3
        center = _obj("center", {(1, 1)}, 2)
        center.attrs["canvas_height"] = 3
        center.attrs["canvas_width"] = 3
        right = _obj("right", {(2, 2)}, 3)
        right.attrs["canvas_height"] = 3
        right.attrs["canvas_width"] = 3
        input_plan = _plan("cc4", [left, center, right])
        output_plan = _plan("cc4", [left, right])
        alignment = Alignment("cc4:pixel_overlap:0", "cc4:pixel_overlap", [("left", "left", 1.0), ("right", "right", 1.0)], ["center"], [], [], [])
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("delete[target=center_object]", programs)
        self.assertIn("delete[target=all,mode=input_center_component]", programs)

    def test_copy_diff_generates_smallest_to_largest_center_candidate(self) -> None:
        small = _obj("small", {(0, 0), (0, 1), (1, 0), (1, 1)}, 2)
        small.attrs["canvas_height"] = 8
        small.attrs["canvas_width"] = 8
        large = _obj("large", {(4, 2), (4, 5), (7, 2), (7, 5)}, 8)
        large.attrs["canvas_height"] = 8
        large.attrs["canvas_width"] = 8
        input_plan = _plan("cc4", [small, large])
        output_plan = _plan("cc4", [small, large])
        alignment = Alignment("cc4:color_shape:0", "cc4:color_shape", [("small", "small", 1.0)], [], [], [], [])
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn(
            "copy[target=smallest_object] ; on_copy: translate[target=all,dx=to_largest_object_center_dx,dy=to_largest_object_center_dy] ; on_original:",
            programs,
        )

    def test_translate_diff_generates_rare_color_to_input_center_candidate(self) -> None:
        rare = _obj("rare", {(0, 4)}, 4)
        rare.attrs["canvas_height"] = 7
        rare.attrs["canvas_width"] = 7
        common_a = _obj("common0", {(1, 1)}, 2)
        common_a.attrs["canvas_height"] = 7
        common_a.attrs["canvas_width"] = 7
        common_b = _obj("common1", {(5, 5)}, 2)
        common_b.attrs["canvas_height"] = 7
        common_b.attrs["canvas_width"] = 7
        output_obj = _obj("out0", {(3, 3)}, 4)
        output_obj.attrs["canvas_height"] = 7
        output_obj.attrs["canvas_width"] = 7
        input_plan = _plan("cc4", [common_a, rare, common_b])
        output_plan = _plan("cc4", [output_obj])
        alignment = Alignment("cc4:bipartite:0", "cc4:bipartite", [("rare", "out0", 1.0)], [], [], [], [])
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("translate[target=rare_color_object,dx=to_input_center_dx,dy=to_input_center_dy]", programs)
        self.assertIn("translate[target=rare_color_object,dx=to_largest_object_center_dx,dy=to_largest_object_center_dy]", programs)

    def test_single_object_internal_shift_generates_rare_color_motif_candidate(self) -> None:
        input_obj = _obj("in0", {(2, 2), (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (4, 2)}, 1)
        input_obj.attrs["canvas_height"] = 7
        input_obj.attrs["canvas_width"] = 7
        output_obj = _obj("out0", {(2, 3), (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (4, 3)}, 1)
        output_obj.attrs["canvas_height"] = 7
        output_obj.attrs["canvas_width"] = 7
        input_plan = _plan("cc4", [input_obj])
        output_plan = _plan("cc4", [output_obj])
        alignment = Alignment("cc4:bipartite:0", "cc4:bipartite", [("in0", "out0", 1.0)], [], [], [], [])
        programs = [render_program(item.program) for item in generate_candidate_transforms(input_plan, output_plan, alignment, 0)]
        self.assertIn("translate[target=all,mode=rare_color_motif_to_largest_component_center]", programs)


if __name__ == "__main__":
    unittest.main()
