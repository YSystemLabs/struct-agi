from __future__ import annotations

from collections import Counter
from dataclasses import replace

from phase1.src.step1.config import ALLOWED_OUTPUT_SIZE_RULES
from phase1.src.step1.data.models import Grid, ObjectData, SegmentationPlan
from phase1.src.step1.layer4.dsl import CopyBlock, PrimitiveCall, Step1Program, validate_step1_program
from phase1.src.step1.layer4.render import infer_output_grid_shape, render_objects


def execute_program(
    program: Step1Program,
    input_plan: SegmentationPlan,
    input_grid: Grid,
    output_size_rule: str,
) -> Grid:
    validate_step1_program(program)
    if output_size_rule not in ALLOWED_OUTPUT_SIZE_RULES:
        raise ValueError(f"Unsupported output size rule for Step 1: {output_size_rule}")

    original_objects = [_clone_object(obj) for obj in input_plan.objects]
    original_objects = _apply_sequence(original_objects, input_grid, program.primitives)

    if program.copy_block is not None:
        original_objects = _apply_copy_block(original_objects, input_grid, program.copy_block)

    rendered_objects = original_objects
    crop_bbox = None
    if output_size_rule == "crop_selected_bbox":
        cropped_objects = [obj for obj in rendered_objects if int(obj.attrs.get("cropped_object", 0)) == 1]
        if cropped_objects:
            rendered_objects = cropped_objects
    if output_size_rule in {"fit_transformed_extent", "crop_selected_bbox"}:
        rendered_objects, crop_bbox = _normalize_objects(rendered_objects)
    elif output_size_rule == "crop_center_cell":
        rendered_objects, crop_bbox = _crop_to_center_cell(input_grid)

    shape = infer_output_grid_shape(input_grid, rendered_objects, output_size_rule, crop_bbox)
    background_color = _background_color(input_grid)
    return render_objects(rendered_objects, background_color, shape)


def _apply_copy_block(objects: list[ObjectData], input_grid: Grid, copy_block: CopyBlock) -> list[ObjectData]:
    target_ids = _resolve_target_ids(objects, copy_block.target, input_grid)
    copies = [_clone_object(obj, suffix="copy") for obj in objects if obj.id in target_ids]
    untouched = [_clone_object(obj) for obj in objects]
    copies = _apply_sequence(copies, input_grid, copy_block.on_copy.primitives, param_context=objects)
    originals = _apply_sequence(untouched, input_grid, copy_block.on_original.primitives, param_context=objects)
    return originals + copies


def _apply_sequence(
    objects: list[ObjectData],
    input_grid: Grid,
    primitives: tuple[PrimitiveCall, ...],
    param_context: list[ObjectData] | None = None,
) -> list[ObjectData]:
    current = [_clone_object(obj) for obj in objects]
    for primitive in primitives:
        current = _apply_primitive(current, input_grid, primitive, param_context or current)
    return current


def _apply_primitive(
    objects: list[ObjectData],
    input_grid: Grid,
    primitive: PrimitiveCall,
    param_context: list[ObjectData],
) -> list[ObjectData]:
    target_ids = _resolve_target_ids(objects, primitive.target, input_grid)
    if primitive.op == "translate" and primitive.params.get("mode") == "rare_color_motif_to_largest_component_center":
        return _translate_rare_color_motif_to_largest_component_center(objects, input_grid, target_ids)
    if primitive.op == "delete" and primitive.params.get("mode") == "input_center_component":
        return _delete_input_center_component(objects, input_grid, target_ids)
    result: list[ObjectData] = []
    for obj in objects:
        if obj.id not in target_ids:
            result.append(_clone_object(obj))
            continue
        transformed = _transform_object(obj, input_grid, primitive, param_context)
        if transformed is None:
            continue
        result.append(transformed)
    return result


def _transform_object(
    obj: ObjectData,
    input_grid: Grid,
    primitive: PrimitiveCall,
    param_context: list[ObjectData],
) -> ObjectData | None:
    if primitive.op == "delete":
        return None
    if primitive.op == "translate":
        dy = _resolve_numeric_param(primitive.params.get("dy", 0), obj, input_grid, param_context)
        dx = _resolve_numeric_param(primitive.params.get("dx", 0), obj, input_grid, param_context)
        pixels = {(row + dy, col + dx) for row, col in obj.pixels}
        return _replace_pixels(obj, pixels)
    if primitive.op == "rotate":
        quarter_turns = int(primitive.params.get("quarter_turns", 1)) % 4
        pixels = set(obj.pixels)
        for _ in range(quarter_turns):
            pixels = _rotate_once(pixels)
        return _replace_pixels(obj, pixels)
    if primitive.op == "flip":
        axis = str(primitive.params.get("axis", "horizontal"))
        return _replace_pixels(obj, _flip_pixels(obj.pixels, axis))
    if primitive.op == "recolor":
        color = int(primitive.params["color"])
        attrs = dict(obj.attrs)
        attrs["color"] = color
        attrs["dominant_color"] = color
        return replace(obj, attrs=attrs)
    if primitive.op == "fill":
        mode = str(primitive.params.get("mode", "bbox_holes"))
        color = int(primitive.params.get("color", obj.attrs.get("dominant_color", 0)))
        pixels = _fill_pixels(obj.pixels, mode)
        attrs = dict(obj.attrs)
        attrs["color"] = color
        attrs["dominant_color"] = color
        return _replace_pixels(replace(obj, attrs=attrs), pixels)
    if primitive.op == "crop":
        mode = str(primitive.params.get("mode", "tight_bbox"))
        return _crop_object(obj, input_grid, mode)
    if primitive.op == "copy":
        raise ValueError("copy must be handled through CopyBlock")
    return _clone_object(obj)


def _clone_object(obj: ObjectData, suffix: str | None = None) -> ObjectData:
    cloned_id = obj.id if suffix is None else f"{obj.id}:{suffix}"
    return ObjectData(
        id=cloned_id,
        pixels=set(obj.pixels),
        bbox=tuple(obj.bbox),
        attrs=dict(obj.attrs),
    )


def _replace_pixels(obj: ObjectData, pixels: set[tuple[int, int]]) -> ObjectData:
    if pixels:
        rows = [row for row, _ in pixels]
        cols = [col for _, col in pixels]
        bbox = (min(rows), min(cols), max(rows), max(cols))
    else:
        bbox = (0, 0, 0, 0)
    attrs = dict(obj.attrs)
    attrs["area"] = len(pixels)
    if pixels:
        attrs["height"] = bbox[2] - bbox[0] + 1
        attrs["width"] = bbox[3] - bbox[1] + 1
        attrs["center_row"] = (bbox[0] + bbox[2]) / 2
        attrs["center_col"] = (bbox[1] + bbox[3]) / 2
    else:
        attrs["height"] = 0
        attrs["width"] = 0
        attrs["center_row"] = 0.0
        attrs["center_col"] = 0.0
    return replace(obj, pixels=pixels, bbox=bbox, attrs=attrs)


def _rotate_once(pixels: set[tuple[int, int]]) -> set[tuple[int, int]]:
    if not pixels:
        return set()
    min_row = min(row for row, _ in pixels)
    min_col = min(col for _, col in pixels)
    max_row = max(row for row, _ in pixels)
    max_col = max(col for _, col in pixels)
    height = max_row - min_row + 1
    normalized = {(row - min_row, col - min_col) for row, col in pixels}
    rotated = {(col, height - 1 - row) for row, col in normalized}
    return {(row + min_row, col + min_col) for row, col in rotated}


def _flip_pixels(pixels: set[tuple[int, int]], axis: str) -> set[tuple[int, int]]:
    if not pixels:
        return set()
    min_row = min(row for row, _ in pixels)
    min_col = min(col for _, col in pixels)
    max_row = max(row for row, _ in pixels)
    max_col = max(col for _, col in pixels)
    if axis == "horizontal":
        return {(row, max_col - (col - min_col)) for row, col in pixels}
    if axis == "vertical":
        return {(max_row - (row - min_row), col) for row, col in pixels}
    raise ValueError(f"Unsupported flip axis: {axis}")


def _fill_pixels(pixels: set[tuple[int, int]], mode: str) -> set[tuple[int, int]]:
    if not pixels:
        return set()
    rows = [row for row, _ in pixels]
    cols = [col for _, col in pixels]
    min_row, max_row = min(rows), max(rows)
    min_col, max_col = min(cols), max(cols)
    if mode == "bbox_holes":
        filled = set(pixels)
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                filled.add((row, col))
        return filled
    if mode == "center_cell":
        center_row = (min_row + max_row) // 2
        center_col = (min_col + max_col) // 2
        return set(pixels) | {(center_row, center_col)}
    raise ValueError(f"Unsupported fill mode: {mode}")


def _crop_object(obj: ObjectData, input_grid: Grid, mode: str) -> ObjectData:
    if mode == "tight_bbox":
        if not obj.pixels:
            return _replace_pixels(obj, set())
        min_row = min(row for row, _ in obj.pixels)
        min_col = min(col for _, col in obj.pixels)
        pixels = {(row - min_row, col - min_col) for row, col in obj.pixels}
        cropped = _replace_pixels(obj, pixels)
        attrs = dict(cropped.attrs)
        attrs["cropped_object"] = 1
        return replace(cropped, attrs=attrs)
    if mode == "center_cell":
        center_row = len(input_grid) // 2
        center_col = len(input_grid[0]) // 2
        color = input_grid[center_row][center_col]
        attrs = dict(obj.attrs)
        attrs["color"] = color
        attrs["dominant_color"] = color
        return _replace_pixels(replace(obj, attrs=attrs), {(0, 0)})
    raise ValueError(f"Unsupported crop mode: {mode}")


def _normalize_objects(
    objects: list[ObjectData],
) -> tuple[list[ObjectData], tuple[int, int, int, int] | None]:
    non_empty = [obj for obj in objects if obj.pixels]
    if not non_empty:
        return (objects, None)
    min_row = min(row for obj in non_empty for row, _ in obj.pixels)
    min_col = min(col for obj in non_empty for _, col in obj.pixels)
    max_row = max(row for obj in non_empty for row, _ in obj.pixels)
    max_col = max(col for obj in non_empty for _, col in obj.pixels)
    normalized = []
    for obj in objects:
        pixels = {(row - min_row, col - min_col) for row, col in obj.pixels}
        normalized.append(_replace_pixels(obj, pixels))
    return (normalized, (min_row, min_col, max_row, max_col))


def _crop_to_center_cell(input_grid: Grid) -> tuple[list[ObjectData], tuple[int, int, int, int]]:
    center_row = len(input_grid) // 2
    center_col = len(input_grid[0]) // 2
    color = input_grid[center_row][center_col]
    obj = ObjectData(
        id="center_cell",
        pixels={(0, 0)},
        bbox=(0, 0, 0, 0),
        attrs={
            "dominant_color": color,
            "color": color,
            "area": 1,
            "height": 1,
            "width": 1,
            "center_row": 0.0,
            "center_col": 0.0,
        },
    )
    return ([obj], (center_row, center_col, center_row, center_col))


def _delete_input_center_component(
    objects: list[ObjectData],
    input_grid: Grid,
    target_ids: set[str],
) -> list[ObjectData]:
    component_pixels = _input_center_component_pixels(input_grid)
    if not component_pixels:
        return [_clone_object(obj) for obj in objects]

    result: list[ObjectData] = []
    for obj in objects:
        if obj.id not in target_ids:
            result.append(_clone_object(obj))
            continue
        remaining_pixels = set(obj.pixels) - component_pixels
        if not remaining_pixels:
            continue
        result.append(_replace_pixels(obj, remaining_pixels))
    return result


def _translate_rare_color_motif_to_largest_component_center(
    objects: list[ObjectData],
    input_grid: Grid,
    target_ids: set[str],
) -> list[ObjectData]:
    if not target_ids:
        return [_clone_object(obj) for obj in objects]

    rare_color = _rare_nonzero_color(input_grid)
    if rare_color is None:
        return [_clone_object(obj) for obj in objects]

    motif_pixels = {
        (row_index, col_index)
        for row_index, row in enumerate(input_grid)
        for col_index, value in enumerate(row)
        if value == rare_color
    }
    anchor_pixels = _largest_nonzero_component_pixels(input_grid)
    if not motif_pixels or not anchor_pixels:
        return [_clone_object(obj) for obj in objects]

    motif_center_row, motif_center_col = _bbox_center(motif_pixels)
    anchor_center_row, anchor_center_col = _bbox_center(anchor_pixels)
    dy = int(round(anchor_center_row - motif_center_row))
    dx = int(round(anchor_center_col - motif_center_col))
    translated_motif = {(row + dy, col + dx) for row, col in motif_pixels}

    result: list[ObjectData] = []
    translated_from_targets = False
    for obj in objects:
        if obj.id not in target_ids:
            result.append(_clone_object(obj))
            continue
        remaining_pixels = set(obj.pixels) - motif_pixels
        if remaining_pixels:
            result.append(_replace_pixels_with_grid_colors(obj, remaining_pixels, input_grid))
        if set(obj.pixels) & motif_pixels:
            translated_from_targets = True

    if not translated_from_targets:
        return [_clone_object(obj) for obj in objects]

    result.append(_build_colored_object("rare_color_motif", translated_motif, rare_color, input_grid))
    return result


def _resolve_target_ids(objects: list[ObjectData], target: str, input_grid: Grid) -> set[str]:
    if target == "all":
        return {obj.id for obj in objects}
    if any(obj.id == target for obj in objects):
        return {target}
    if target == "center_object":
        selected = _select_center_object(objects, input_grid)
        return {selected.id} if selected is not None else set()
    if target == "smallest_object":
        selected = _select_extreme_object(objects, smallest=True)
        return {selected.id} if selected is not None else set()
    if target == "rare_color_object":
        selected = _select_rare_color_object(objects)
        return {selected.id} if selected is not None else set()
    return set()


def _background_color(input_grid: Grid) -> int:
    return 0


def _rare_nonzero_color(input_grid: Grid) -> int | None:
    color_counts = Counter(
        value
        for row in input_grid
        for value in row
        if value != _background_color(input_grid)
    )
    if not color_counts:
        return None
    return min(color_counts, key=lambda color: (color_counts[color], color))


def _largest_nonzero_component_pixels(input_grid: Grid) -> set[tuple[int, int]]:
    if not input_grid or not input_grid[0]:
        return set()

    rows = len(input_grid)
    cols = len(input_grid[0])
    visited: set[tuple[int, int]] = set()
    largest: set[tuple[int, int]] = set()
    for row in range(rows):
        for col in range(cols):
            if input_grid[row][col] == _background_color(input_grid) or (row, col) in visited:
                continue
            component: set[tuple[int, int]] = set()
            pending = [(row, col)]
            visited.add((row, col))
            while pending:
                current_row, current_col = pending.pop()
                component.add((current_row, current_col))
                for delta_row, delta_col in (
                    (-1, -1),
                    (-1, 0),
                    (-1, 1),
                    (0, -1),
                    (0, 1),
                    (1, -1),
                    (1, 0),
                    (1, 1),
                ):
                    next_row = current_row + delta_row
                    next_col = current_col + delta_col
                    next_cell = (next_row, next_col)
                    if not (0 <= next_row < rows and 0 <= next_col < cols):
                        continue
                    if input_grid[next_row][next_col] == _background_color(input_grid) or next_cell in visited:
                        continue
                    visited.add(next_cell)
                    pending.append(next_cell)
            if not largest or _component_sort_key(component) > _component_sort_key(largest):
                largest = component
    return largest


def _input_center_component_pixels(input_grid: Grid) -> set[tuple[int, int]]:
    if not input_grid or not input_grid[0]:
        return set()

    center_row = len(input_grid) // 2
    center_col = len(input_grid[0]) // 2
    center_color = input_grid[center_row][center_col]
    if center_color == _background_color(input_grid):
        return set()

    component: set[tuple[int, int]] = set()
    pending = [(center_row, center_col)]
    while pending:
        row, col = pending.pop()
        if (row, col) in component:
            continue
        if input_grid[row][col] != center_color:
            continue
        component.add((row, col))
        for delta_row, delta_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            next_row = row + delta_row
            next_col = col + delta_col
            if 0 <= next_row < len(input_grid) and 0 <= next_col < len(input_grid[0]):
                pending.append((next_row, next_col))
    return component


def _component_sort_key(component: set[tuple[int, int]]) -> tuple[int, float, float, tuple[int, int, int, int]]:
    center_row, center_col = _bbox_center(component)
    min_row = min(row for row, _ in component)
    min_col = min(col for _, col in component)
    max_row = max(row for row, _ in component)
    max_col = max(col for _, col in component)
    return (len(component), center_row, center_col, (-min_row, -min_col, -max_row, -max_col))


def _bbox_center(pixels: set[tuple[int, int]]) -> tuple[float, float]:
    min_row = min(row for row, _ in pixels)
    min_col = min(col for _, col in pixels)
    max_row = max(row for row, _ in pixels)
    max_col = max(col for _, col in pixels)
    return ((min_row + max_row) / 2, (min_col + max_col) / 2)


def _replace_pixels_with_grid_colors(obj: ObjectData, pixels: set[tuple[int, int]], input_grid: Grid) -> ObjectData:
    replaced = _replace_pixels(obj, pixels)
    if not pixels:
        return replaced
    colors = Counter(input_grid[row][col] for row, col in pixels)
    dominant_color = min(
        (color for color in colors),
        key=lambda color: (-colors[color], color),
    )
    attrs = dict(replaced.attrs)
    attrs["dominant_color"] = dominant_color
    attrs["color"] = dominant_color
    return replace(replaced, attrs=attrs)


def _build_colored_object(object_id: str, pixels: set[tuple[int, int]], color: int, input_grid: Grid) -> ObjectData:
    rows = [row for row, _ in pixels]
    cols = [col for _, col in pixels]
    bbox = (min(rows), min(cols), max(rows), max(cols))
    return ObjectData(
        id=object_id,
        pixels=set(pixels),
        bbox=bbox,
        attrs={
            "dominant_color": color,
            "color": color,
            "area": len(pixels),
            "height": bbox[2] - bbox[0] + 1,
            "width": bbox[3] - bbox[1] + 1,
            "center_row": (bbox[0] + bbox[2]) / 2,
            "center_col": (bbox[1] + bbox[3]) / 2,
            "canvas_height": len(input_grid),
            "canvas_width": len(input_grid[0]) if input_grid else 0,
        },
    )


def _resolve_numeric_param(value: object, obj: ObjectData, input_grid: Grid, param_context: list[ObjectData]) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        sign = -1 if value.startswith("-") else 1
        token = value[1:] if sign == -1 else value
        resolved = _symbolic_param_value(token, obj, input_grid, param_context)
        return sign * resolved
    raise ValueError(f"Unsupported Step 1 numeric parameter: {value!r}")


def _symbolic_param_value(token: str, obj: ObjectData, input_grid: Grid, param_context: list[ObjectData]) -> int:
    if token == "input_width":
        return len(input_grid[0]) if input_grid else 0
    if token == "input_height":
        return len(input_grid)
    if token == "object_width":
        return int(obj.attrs.get("width", 0))
    if token == "object_height":
        return int(obj.attrs.get("height", 0))
    if token == "to_input_center_dx":
        return int(round(((len(input_grid[0]) - 1) / 2) - float(obj.attrs.get("center_col", 0.0)))) if input_grid else 0
    if token == "to_input_center_dy":
        return int(round(((len(input_grid) - 1) / 2) - float(obj.attrs.get("center_row", 0.0))))
    if token == "to_largest_object_center_dx":
        largest = _select_extreme_object(param_context, smallest=False)
        if largest is None:
            return 0
        return int(round(float(largest.attrs.get("center_col", 0.0)) - float(obj.attrs.get("center_col", 0.0))))
    if token == "to_largest_object_center_dy":
        largest = _select_extreme_object(param_context, smallest=False)
        if largest is None:
            return 0
        return int(round(float(largest.attrs.get("center_row", 0.0)) - float(obj.attrs.get("center_row", 0.0))))
    raise ValueError(f"Unsupported Step 1 symbolic parameter: {token}")


def _select_center_object(objects: list[ObjectData], input_grid: Grid) -> ObjectData | None:
    if not objects or not input_grid:
        return None
    center_row = (len(input_grid) - 1) / 2
    center_col = (len(input_grid[0]) - 1) / 2
    return min(
        objects,
        key=lambda obj: (
            min(
                abs(row - center_row) + abs(col - center_col)
                for row, col in obj.pixels
            ),
            int(obj.attrs.get("area", 0)),
            obj.bbox,
            obj.id,
        ),
    )


def _select_extreme_object(objects: list[ObjectData], smallest: bool) -> ObjectData | None:
    if not objects:
        return None
    if smallest:
        return min(objects, key=lambda obj: (int(obj.attrs.get("area", 0)), obj.bbox, obj.id))
    return max(objects, key=lambda obj: (int(obj.attrs.get("area", 0)), tuple(-value for value in obj.bbox), obj.id))


def _select_rare_color_object(objects: list[ObjectData]) -> ObjectData | None:
    if not objects:
        return None
    color_counts = Counter(int(obj.attrs.get("dominant_color", 0)) for obj in objects)
    return min(
        objects,
        key=lambda obj: (
            color_counts[int(obj.attrs.get("dominant_color", 0))],
            int(obj.attrs.get("area", 0)),
            obj.bbox,
            obj.id,
        ),
    )
