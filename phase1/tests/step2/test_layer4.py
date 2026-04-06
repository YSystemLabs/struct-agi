from __future__ import annotations

import unittest

from phase1.src.step2.data.models import ObjectData, SegmentationPlan
from phase1.src.step2.layer4.dsl import CopyBlock, CopyClause, PrimitiveCall, Step1Program, parse_program, render_program, validate_step1_program
from phase1.src.step2.layer4.executor import execute_program
from phase1.src.step2.layer4.render import infer_output_grid_shape, render_objects


def _build_plan(grid: list[list[int]]) -> SegmentationPlan:
    pixels = {
        (row_index, col_index)
        for row_index, row in enumerate(grid)
        for col_index, value in enumerate(row)
        if value != 0
    }
    rows = [row for row, _ in pixels] or [0]
    cols = [col for _, col in pixels] or [0]
    obj = ObjectData(
        id="obj0",
        pixels=pixels,
        bbox=(min(rows), min(cols), max(rows), max(cols)),
        attrs={
            "dominant_color": next((value for row in grid for value in row if value != 0), 0),
            "color": next((value for row in grid for value in row if value != 0), 0),
            "area": len(pixels),
            "height": max(rows) - min(rows) + 1,
            "width": max(cols) - min(cols) + 1,
            "center_row": (min(rows) + max(rows)) / 2,
            "center_col": (min(cols) + max(cols)) / 2,
        },
    )
    return SegmentationPlan(plan_id="whole_grid", method="whole_grid", objects=[obj], relations=[])


def _manual_object(object_id: str, pixels: set[tuple[int, int]], color: int, canvas_height: int, canvas_width: int) -> ObjectData:
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
            "canvas_height": canvas_height,
            "canvas_width": canvas_width,
        },
    )


def _multi_object_plan(objects: list[ObjectData]) -> SegmentationPlan:
    return SegmentationPlan(plan_id="cc4", method="cc4", objects=objects, relations=[])


class Layer4Tests(unittest.TestCase):
    def test_render_objects_background_and_overlap_order(self) -> None:
        first = ObjectData(
            id="a",
            pixels={(0, 0), (0, 1), (1, 0), (1, 1)},
            bbox=(0, 0, 1, 1),
            attrs={"dominant_color": 1, "color": 1, "area": 4},
        )
        second = ObjectData(
            id="b",
            pixels={(1, 1)},
            bbox=(1, 1, 1, 1),
            attrs={"dominant_color": 2, "color": 2, "area": 1},
        )
        grid = render_objects([first, second], 0, (3, 3), program_order=["a", "b"])
        self.assertEqual([[1, 1, 0], [1, 2, 0], [0, 0, 0]], grid)

    def test_infer_output_grid_shape_supports_all_rules(self) -> None:
        plan = _build_plan([[1, 0, 0], [1, 0, 0]])
        self.assertEqual((2, 3), infer_output_grid_shape([[1, 0, 0], [1, 0, 0]], plan.objects, "preserve_input_size"))
        self.assertEqual((2, 1), infer_output_grid_shape([[1, 0, 0], [1, 0, 0]], plan.objects, "fit_transformed_extent"))
        self.assertEqual((2, 1), infer_output_grid_shape([[1, 0, 0], [1, 0, 0]], plan.objects, "crop_selected_bbox", (0, 0, 1, 0)))
        self.assertEqual((1, 1), infer_output_grid_shape([[1, 0, 0], [1, 0, 0]], plan.objects, "crop_center_cell"))

    def test_translate_primitive(self) -> None:
        grid = [[2, 0, 0], [2, 0, 0], [0, 0, 0]]
        program = Step1Program(primitives=(PrimitiveCall("translate", params={"dx": 1}),))
        output = execute_program(program, _build_plan(grid), grid, "preserve_input_size")
        self.assertEqual([[0, 2, 0], [0, 2, 0], [0, 0, 0]], output)

    def test_dynamic_background_color_is_taken_from_segmentation_plan(self) -> None:
        grid = [[2, 5, 2], [2, 2, 2]]
        obj = _manual_object("obj0", {(0, 1)}, 5, 2, 3)
        plan = SegmentationPlan(plan_id="bg_fg", method="bg_fg", objects=[obj], relations=[], bg_color=2)
        program = Step1Program(primitives=(PrimitiveCall("delete"),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual([[2, 2, 2], [2, 2, 2]], output)

    def test_copy_then_translate_by_width(self) -> None:
        grid = [[3, 0, 3]]
        program = Step1Program(
            copy_block=CopyBlock(
                on_copy=CopyClause(primitives=(PrimitiveCall("translate", params={"dx": 3}),)),
                on_original=CopyClause(),
            )
        )
        output = execute_program(program, _build_plan(grid), grid, "fit_transformed_extent")
        self.assertEqual([[3, 0, 3, 3, 0, 3]], output)

    def test_copy_then_translate_by_symbolic_input_width(self) -> None:
        grid = [[3, 0, 3]]
        program = Step1Program(
            copy_block=CopyBlock(
                on_copy=CopyClause(primitives=(PrimitiveCall("translate", params={"dx": "input_width"}),)),
                on_original=CopyClause(),
            )
        )
        output = execute_program(program, _build_plan(grid), grid, "fit_transformed_extent")
        self.assertEqual([[3, 0, 3, 3, 0, 3]], output)

    def test_translate_by_symbolic_negative_object_height(self) -> None:
        grid = [[0, 0, 0], [0, 0, 0], [0, 8, 0], [0, 8, 0]]
        program = Step1Program(primitives=(PrimitiveCall("translate", params={"dy": "-object_height"}),))
        output = execute_program(program, _build_plan(grid), grid, "preserve_input_size")
        self.assertEqual([[0, 8, 0], [0, 8, 0], [0, 0, 0], [0, 0, 0]], output)

    def test_delete_center_object_selector(self) -> None:
        grid = [[1, 0, 0], [0, 2, 0], [0, 0, 3]]
        plan = _multi_object_plan(
            [
                _manual_object("left", {(0, 0)}, 1, 3, 3),
                _manual_object("center", {(1, 1)}, 2, 3, 3),
                _manual_object("right", {(2, 2)}, 3, 3, 3),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("delete", target="center_object"),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual([[1, 0, 0], [0, 0, 0], [0, 0, 3]], output)

    def test_delete_largest_object_selector(self) -> None:
        grid = [[4, 4, 0], [4, 4, 0], [0, 0, 7]]
        plan = _multi_object_plan(
            [
                _manual_object("large", {(0, 0), (0, 1), (1, 0), (1, 1)}, 4, 3, 3),
                _manual_object("small", {(2, 2)}, 7, 3, 3),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("delete", target="largest_object"),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual([[0, 0, 0], [0, 0, 0], [0, 0, 7]], output)

    def test_extend_to_boundary_gap_thinner_object_selector(self) -> None:
        grid = [
            [0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 2, 0, 0],
            [0, 0, 0, 2, 0, 0],
            [0, 0, 0, 2, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("bar", {(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)}, 1, 6, 6),
                _manual_object("stem", {(3, 3), (4, 3), (5, 3)}, 2, 6, 6),
            ]
        )
        program = Step1Program(
            primitives=(
                PrimitiveCall(
                    "extend_to_boundary",
                    target="gap_thinner_object",
                    params={"source": "center_col", "direction": "to_nearest_object_boundary"},
                ),
            )
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0, 0],
                [1, 1, 1, 1, 1, 0],
                [0, 0, 0, 2, 0, 0],
                [0, 0, 0, 2, 0, 0],
                [0, 0, 0, 2, 0, 0],
                [0, 0, 0, 2, 0, 0],
            ],
            output,
        )

    def test_extend_to_boundary_right(self) -> None:
        grid = [[0, 0, 0, 0], [0, 3, 0, 0], [0, 0, 0, 0]]
        plan = _multi_object_plan([_manual_object("obj0", {(1, 1)}, 3, 3, 4)])
        program = Step1Program(primitives=(PrimitiveCall("extend_to_boundary", params={"source": "full_boundary", "direction": "right"}),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual([[0, 0, 0, 0], [0, 3, 3, 3], [0, 0, 0, 0]], output)

    def test_extend_to_boundary_stops_at_other_object(self) -> None:
        grid = [
            [0, 0, 0, 0, 0],
            [0, 3, 0, 9, 0],
            [0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("src", {(1, 1)}, 3, 3, 5),
                _manual_object("blocker", {(1, 3)}, 9, 3, 5),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("extend_to_boundary", target="src", params={"source": "full_boundary", "direction": "right"}),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0],
                [0, 3, 3, 9, 0],
                [0, 0, 0, 0, 0],
            ],
            output,
        )

    def test_extend_to_boundary_nearest_boundary_uses_documented_tie_break(self) -> None:
        grid = [
            [0, 0, 0],
            [0, 8, 0],
            [0, 0, 0],
        ]
        plan = _multi_object_plan([_manual_object("obj0", {(1, 1)}, 8, 3, 3)])
        program = Step1Program(primitives=(PrimitiveCall("extend_to_boundary", params={"source": "full_boundary", "direction": "nearest_boundary"}),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 8, 0],
                [0, 8, 0],
                [0, 0, 0],
            ],
            output,
        )

    def test_extend_to_boundary_to_nearest_object_boundary_prefers_overlapping_axis(self) -> None:
        grid = [
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 4, 0, 0, 9, 0],
            [0, 0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("src", {(2, 1)}, 4, 4, 6),
                _manual_object("target", {(2, 4)}, 9, 4, 6),
            ]
        )
        program = Step1Program(
            primitives=(PrimitiveCall("extend_to_boundary", target="src", params={"source": "full_boundary", "direction": "to_nearest_object_boundary"}),)
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 4, 4, 4, 9, 0],
                [0, 0, 0, 0, 0, 0],
            ],
            output,
        )

    def test_extend_to_boundary_horizontal_both_extends_independently(self) -> None:
        grid = [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 9, 0, 0, 8, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("src", {(1, 3)}, 5, 3, 7),
                _manual_object("left_block", {(1, 2)}, 9, 3, 7),
                _manual_object("right_block", {(1, 5)}, 8, 3, 7),
            ]
        )
        program = Step1Program(
            primitives=(PrimitiveCall("extend_to_boundary", target="src", params={"source": "full_boundary", "direction": "horizontal_both"}),)
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0, 0, 0],
                [0, 0, 9, 5, 5, 8, 0],
                [0, 0, 0, 0, 0, 0, 0],
            ],
            output,
        )

    def test_validate_program_rejects_unknown_extend_direction(self) -> None:
        with self.assertRaises(ValueError):
            validate_step1_program(
                Step1Program(primitives=(PrimitiveCall("extend_to_boundary", params={"source": "full_boundary", "direction": "diagonal"}),))
            )

    def test_validate_program_rejects_unknown_extend_source(self) -> None:
        with self.assertRaises(ValueError):
            validate_step1_program(
                Step1Program(primitives=(PrimitiveCall("extend_to_boundary", params={"source": "mask:custom", "direction": "right"}),))
            )

    def test_extend_to_boundary_center_row_extends_only_middle_row(self) -> None:
        grid = [
            [0, 0, 0, 0, 0, 0],
            [0, 5, 5, 5, 0, 0],
            [0, 5, 5, 5, 0, 0],
            [0, 5, 5, 5, 0, 0],
            [0, 0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan([_manual_object("obj0", {(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3)}, 5, 5, 6)])
        program = Step1Program(
            primitives=(PrimitiveCall("extend_to_boundary", params={"source": "center_row", "direction": "right"}),)
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0, 0],
                [0, 5, 5, 5, 0, 0],
                [0, 5, 5, 5, 5, 5],
                [0, 5, 5, 5, 0, 0],
                [0, 0, 0, 0, 0, 0],
            ],
            output,
        )

    def test_extend_to_boundary_bottom_edge_extends_toward_nearest_object(self) -> None:
        grid = [
            [0, 6, 0, 0, 0, 0],
            [0, 6, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [3, 3, 3, 3, 3, 0],
            [0, 0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("vert", {(0, 1), (1, 1)}, 6, 6, 6),
                _manual_object("horiz", {(4, 0), (4, 1), (4, 2), (4, 3), (4, 4)}, 3, 6, 6),
            ]
        )
        program = Step1Program(
            primitives=(PrimitiveCall("extend_to_boundary", target="vert", params={"source": "bottom_edge", "direction": "to_nearest_object_boundary"}),)
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 6, 0, 0, 0, 0],
                [0, 6, 0, 0, 0, 0],
                [0, 6, 0, 0, 0, 0],
                [0, 6, 0, 0, 0, 0],
                [3, 3, 3, 3, 3, 0],
                [0, 0, 0, 0, 0, 0],
            ],
            output,
        )

    def test_translate_to_boundary_symbol_moves_asymmetric_object_to_canvas_edge(self) -> None:
        grid = [
            [0, 0, 0, 0, 0],
            [0, 4, 0, 0, 0],
            [0, 4, 4, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan([_manual_object("obj0", {(1, 1), (2, 1), (2, 2)}, 4, 4, 5)])
        program = Step1Program(primitives=(PrimitiveCall("translate", target="all", params={"dx": "to_boundary_dx", "dy": "to_boundary_dy"}),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0],
                [0, 0, 0, 4, 0],
                [0, 0, 0, 4, 4],
                [0, 0, 0, 0, 0],
            ],
            output,
        )

    def test_translate_to_boundary_symbol_moves_multiple_objects_to_shared_direction(self) -> None:
        grid = [
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 7, 0, 0, 0],
            [0, 7, 0, 8, 0],
            [0, 7, 0, 8, 0],
            [0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("left", {(2, 1), (3, 1), (4, 1)}, 7, 6, 5),
                _manual_object("right", {(3, 3), (4, 3)}, 8, 6, 5),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("translate", target="all", params={"dx": "to_boundary_dx", "dy": "to_boundary_dy"}),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 7, 0, 0, 0],
                [0, 7, 0, 8, 0],
                [0, 7, 0, 8, 0],
            ],
            output,
        )

    def test_translate_to_nearest_object_symbol_moves_only_selected_mover(self) -> None:
        grid = [
            [5, 0, 0, 0, 2],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 9, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("mover", {(0, 0)}, 5, 5, 5),
                _manual_object("near", {(0, 4)}, 2, 5, 5),
                _manual_object("far", {(4, 2)}, 9, 5, 5),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("translate", target="all", params={"dx": "to_nearest_object_dx", "dy": "to_nearest_object_dy"}),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 5, 2],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 9, 0, 0],
            ],
            output,
        )

    def test_delete_noise_objects_selector_removes_small_objects(self) -> None:
        grid = [
            [7, 7, 7, 0, 8, 8, 8],
            [7, 7, 7, 0, 8, 8, 8],
            [7, 7, 7, 0, 8, 8, 8],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 3, 0],
            [0, 0, 0, 0, 0, 0, 4],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("large0", {(r, c) for r in range(3) for c in range(3)}, 7, 6, 7),
                _manual_object("large1", {(r, c) for r in range(3) for c in range(4, 7)}, 8, 6, 7),
                _manual_object("noise0", {(4, 5)}, 3, 6, 7),
                _manual_object("noise1", {(5, 6)}, 4, 6, 7),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("delete", target="noise_objects"),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(0, output[4][5])
        self.assertEqual(0, output[5][6])

    def test_delete_boundary_adjacent_selector_removes_border_objects(self) -> None:
        grid = [
            [8, 0, 0],
            [0, 5, 0],
            [0, 0, 9],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("top_left", {(0, 0)}, 8, 3, 3),
                _manual_object("center", {(1, 1)}, 5, 3, 3),
                _manual_object("bottom_right", {(2, 2)}, 9, 3, 3),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("delete", target="boundary_adjacent"),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual([[0, 0, 0], [0, 5, 0], [0, 0, 0]], output)

    def test_translate_with_noise_objects_selector_is_rejected(self) -> None:
        grid = [[1, 0], [0, 2]]
        plan = _multi_object_plan(
            [
                _manual_object("a", {(0, 0)}, 1, 2, 2),
                _manual_object("b", {(1, 1)}, 2, 2, 2),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("translate", target="noise_objects", params={"dx": 1}),))
        with self.assertRaises(ValueError):
            execute_program(program, plan, grid, "preserve_input_size")

    def test_parse_program_supports_three_primitives_and_extend(self) -> None:
        program = parse_program(
            "recolor[target=all,color=3] ; translate[target=all,dx=1,dy=0] ; extend_to_boundary[target=all,direction=right]"
        )
        self.assertEqual(("recolor", "translate", "extend_to_boundary"), tuple(item.op for item in program.primitives))

    def test_delete_input_center_component_removes_center_line(self) -> None:
        grid = [
            [0, 0, 0, 0, 0, 0, 6, 0, 0],
            [0, 2, 0, 0, 0, 0, 6, 0, 0],
            [0, 2, 0, 0, 0, 0, 6, 0, 0],
            [0, 2, 0, 0, 7, 0, 0, 0, 0],
            [0, 0, 0, 0, 7, 0, 0, 0, 0],
            [0, 0, 0, 0, 7, 0, 4, 0, 0],
            [0, 0, 0, 0, 0, 0, 4, 0, 0],
            [0, 0, 0, 0, 9, 0, 0, 0, 0],
            [0, 0, 0, 0, 9, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("six", {(0, 6), (1, 6), (2, 6)}, 6, 9, 9),
                _manual_object("two", {(1, 1), (2, 1), (3, 1)}, 2, 9, 9),
                _manual_object("seven", {(3, 4), (4, 4), (5, 4)}, 7, 9, 9),
                _manual_object("four", {(5, 6), (6, 6)}, 4, 9, 9),
                _manual_object("nine", {(7, 4), (8, 4)}, 9, 9, 9),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("delete", params={"mode": "input_center_component"}),))
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0, 0, 6, 0, 0],
                [0, 2, 0, 0, 0, 0, 6, 0, 0],
                [0, 2, 0, 0, 0, 0, 6, 0, 0],
                [0, 2, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 4, 0, 0],
                [0, 0, 0, 0, 0, 0, 4, 0, 0],
                [0, 0, 0, 0, 9, 0, 0, 0, 0],
                [0, 0, 0, 0, 9, 0, 0, 0, 0],
            ],
            output,
        )

    def test_delete_input_center_component_removes_single_center_cell(self) -> None:
        grid = [[2, 2, 2], [2, 8, 2], [2, 2, 2]]
        program = Step1Program(primitives=(PrimitiveCall("delete", params={"mode": "input_center_component"}),))
        output = execute_program(program, _build_plan(grid), grid, "preserve_input_size")
        self.assertEqual([[2, 2, 2], [2, 0, 2], [2, 2, 2]], output)

    def test_copy_smallest_object_to_largest_object_center(self) -> None:
        grid = [
            [2, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 8, 0, 8],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 8, 0, 8],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("small", {(0, 0)}, 2, 6, 6),
                _manual_object("large", {(3, 3), (3, 5), (5, 3), (5, 5)}, 8, 6, 6),
            ]
        )
        program = Step1Program(
            copy_block=CopyBlock(
                target="smallest_object",
                on_copy=CopyClause(
                    primitives=(
                        PrimitiveCall(
                            "translate",
                            params={"dx": "to_largest_object_center_dx", "dy": "to_largest_object_center_dy"},
                        ),
                    ),
                ),
                on_original=CopyClause(),
            )
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(2, output[4][4])

    def test_translate_rare_color_object_to_input_center(self) -> None:
        grid = [
            [0, 0, 0, 0, 4],
            [0, 2, 0, 2, 0],
            [0, 0, 0, 0, 0],
            [0, 2, 0, 2, 0],
            [0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("common0", {(1, 1)}, 2, 5, 5),
                _manual_object("common1", {(1, 3)}, 2, 5, 5),
                _manual_object("common2", {(3, 1)}, 2, 5, 5),
                _manual_object("common3", {(3, 3)}, 2, 5, 5),
                _manual_object("rare", {(0, 4)}, 4, 5, 5),
            ]
        )
        program = Step1Program(
            primitives=(
                PrimitiveCall(
                    "translate",
                    target="rare_color_object",
                    params={"dx": "to_input_center_dx", "dy": "to_input_center_dy"},
                ),
            )
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(4, output[2][2])

    def test_translate_rare_color_object_to_largest_object_center(self) -> None:
        grid = [
            [0, 0, 0, 0, 0, 0, 4],
            [0, 0, 2, 0, 2, 0, 0],
            [0, 0, 0, 2, 0, 0, 0],
            [0, 2, 0, 0, 0, 2, 0],
            [0, 0, 2, 0, 2, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("shape", {(1, 2), (1, 4), (2, 3), (3, 1), (3, 5), (4, 2), (4, 4)}, 2, 7, 7),
                _manual_object("rare", {(0, 6)}, 4, 7, 7),
            ]
        )
        program = Step1Program(
            primitives=(
                PrimitiveCall(
                    "translate",
                    target="rare_color_object",
                    params={"dx": "to_largest_object_center_dx", "dy": "to_largest_object_center_dy"},
                ),
            )
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(4, output[2][3])

    def test_translate_rare_color_motif_to_largest_component_center(self) -> None:
        grid = [
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 3, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1],
            [0, 0, 3, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("shape", {(2, 2), (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (4, 2)}, 1, 7, 7),
            ]
        )
        program = Step1Program(
            primitives=(
                PrimitiveCall(
                    "translate",
                    params={"mode": "rare_color_motif_to_largest_component_center"},
                ),
            )
        )
        output = execute_program(program, plan, grid, "preserve_input_size")
        self.assertEqual(
            [
                [0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 3, 0, 0, 0],
                [1, 1, 1, 1, 1, 1, 1],
                [0, 0, 0, 3, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0],
            ],
            output,
        )

    def test_crop_selected_bbox_keeps_only_cropped_object(self) -> None:
        grid = [
            [1, 0, 0, 0, 0],
            [0, 2, 2, 0, 0],
            [0, 2, 2, 0, 0],
            [0, 0, 0, 0, 3],
            [0, 0, 0, 0, 0],
        ]
        plan = _multi_object_plan(
            [
                _manual_object("left", {(0, 0)}, 1, 5, 5),
                _manual_object("center", {(1, 1), (1, 2), (2, 1), (2, 2)}, 2, 5, 5),
                _manual_object("right", {(3, 4)}, 3, 5, 5),
            ]
        )
        program = Step1Program(primitives=(PrimitiveCall("crop", target="center_object", params={"mode": "tight_bbox"}),))
        output = execute_program(program, plan, grid, "crop_selected_bbox")
        self.assertEqual([[2, 2], [2, 2]], output)

    def test_recolor_primitive(self) -> None:
        grid = [[1, 1], [0, 0]]
        program = Step1Program(primitives=(PrimitiveCall("recolor", params={"color": 2}),))
        output = execute_program(program, _build_plan(grid), grid, "preserve_input_size")
        self.assertEqual([[2, 2], [0, 0]], output)

    def test_delete_primitive(self) -> None:
        grid = [[4, 4], [0, 0]]
        program = Step1Program(primitives=(PrimitiveCall("delete"),))
        output = execute_program(program, _build_plan(grid), grid, "preserve_input_size")
        self.assertEqual([[0, 0], [0, 0]], output)

    def test_rotate_primitive(self) -> None:
        grid = [[5, 5, 0], [5, 0, 0]]
        program = Step1Program(primitives=(PrimitiveCall("rotate", params={"quarter_turns": 1}),))
        output = execute_program(program, _build_plan(grid), grid, "fit_transformed_extent")
        self.assertEqual([[5, 5], [0, 5]], output)

    def test_flip_primitive(self) -> None:
        grid = [[6, 0, 0], [6, 6, 0]]
        program = Step1Program(primitives=(PrimitiveCall("flip", params={"axis": "horizontal"}),))
        output = execute_program(program, _build_plan(grid), grid, "fit_transformed_extent")
        self.assertEqual([[0, 6], [6, 6]], output)

    def test_fill_primitive(self) -> None:
        grid = [[7, 7, 7], [7, 0, 7], [7, 7, 7]]
        program = Step1Program(primitives=(PrimitiveCall("fill", params={"mode": "bbox_holes", "color": 7}),))
        output = execute_program(program, _build_plan(grid), grid, "preserve_input_size")
        self.assertEqual([[7, 7, 7], [7, 7, 7], [7, 7, 7]], output)

    def test_crop_center_cell_rule(self) -> None:
        grid = [[0, 0, 0], [0, 8, 0], [0, 0, 0]]
        program = Step1Program(primitives=(PrimitiveCall("crop", params={"mode": "center_cell"}),))
        output = execute_program(program, _build_plan(grid), grid, "crop_center_cell")
        self.assertEqual([[8]], output)

    def test_crop_tight_bbox(self) -> None:
        grid = [[0, 0, 0, 0], [0, 9, 9, 0], [0, 9, 9, 0], [0, 0, 0, 0]]
        program = Step1Program(primitives=(PrimitiveCall("crop", params={"mode": "tight_bbox"}),))
        output = execute_program(program, _build_plan(grid), grid, "crop_selected_bbox")
        self.assertEqual([[9, 9], [9, 9]], output)

    def test_bare_copy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_step1_program(Step1Program(primitives=(PrimitiveCall("copy"),)))

    def test_forbidden_control_flow_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_step1_program(Step1Program(primitives=(PrimitiveCall("translate", target="If"),)))

    def test_render_program_is_stable(self) -> None:
        program = Step1Program(
            primitives=(PrimitiveCall("recolor", params={"color": 3}),),
            copy_block=CopyBlock(on_copy=CopyClause(primitives=(PrimitiveCall("translate", params={"dx": 1}),))),
        )
        rendered = render_program(program)
        self.assertIn("recolor[target=all,color=3]", rendered)
        self.assertIn("copy[target=all]", rendered)


if __name__ == "__main__":
    unittest.main()
