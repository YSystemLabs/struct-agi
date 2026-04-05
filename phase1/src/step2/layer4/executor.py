from __future__ import annotations

from collections import Counter
from dataclasses import replace

from phase1.src.step2.config import ALLOWED_OUTPUT_SIZE_RULES
from phase1.src.step2.data.models import Grid, ObjectData, SegmentationPlan
from phase1.src.step2.layer4.dsl import CopyBlock, PrimitiveCall, Step1Program, validate_step1_program
from phase1.src.step2.layer4.render import infer_output_grid_shape, render_objects


def execute_program(
    program: Step1Program,
    input_plan: SegmentationPlan,
    input_grid: Grid,
    output_size_rule: str,
) -> Grid:
    validate_step1_program(program)
    if output_size_rule not in ALLOWED_OUTPUT_SIZE_RULES:
        raise ValueError(f"Unsupported output size rule for Step 1: {output_size_rule}")

    background_color = _background_color(input_grid, input_plan)
    original_objects = [_clone_object(obj) for obj in input_plan.objects]
    original_objects = _apply_sequence(original_objects, input_grid, program.primitives, background_color=background_color)

    if program.copy_block is not None:
        original_objects = _apply_copy_block(original_objects, input_grid, program.copy_block, background_color)

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
    return render_objects(rendered_objects, background_color, shape)


def _apply_copy_block(objects: list[ObjectData], input_grid: Grid, copy_block: CopyBlock, background_color: int) -> list[ObjectData]:
    target_ids = _resolve_target_ids(objects, copy_block.target, input_grid)
    copies = [_clone_object(obj, suffix="copy") for obj in objects if obj.id in target_ids]
    untouched = [_clone_object(obj) for obj in objects]
    copies = _apply_sequence(copies, input_grid, copy_block.on_copy.primitives, param_context=objects, background_color=background_color)
    originals = _apply_sequence(untouched, input_grid, copy_block.on_original.primitives, param_context=objects, background_color=background_color)
    return originals + copies


def _apply_sequence(
    objects: list[ObjectData],
    input_grid: Grid,
    primitives: tuple[PrimitiveCall, ...],
    param_context: list[ObjectData] | None = None,
    background_color: int = 0,
) -> list[ObjectData]:
    current = [_clone_object(obj) for obj in objects]
    for primitive in primitives:
        current = _apply_primitive(current, input_grid, primitive, param_context or current, background_color)
    return current


def _apply_primitive(
    objects: list[ObjectData],
    input_grid: Grid,
    primitive: PrimitiveCall,
    param_context: list[ObjectData],
    background_color: int,
) -> list[ObjectData]:
    target_ids = _resolve_target_ids(objects, primitive.target, input_grid)
    if primitive.op == "translate" and primitive.params.get("mode") == "rare_color_motif_to_largest_component_center":
        return _translate_rare_color_motif_to_largest_component_center(objects, input_grid, target_ids, background_color)
    if primitive.op == "delete" and primitive.params.get("mode") == "input_center_component":
        return _delete_input_center_component(objects, input_grid, target_ids, background_color)
    result: list[ObjectData] = []
    for obj in objects:
        if obj.id not in target_ids:
            result.append(_clone_object(obj))
            continue
        transformed = _transform_object(obj, input_grid, primitive, param_context, background_color)
        if transformed is None:
            continue
        result.append(transformed)
    return result


def _transform_object(
    obj: ObjectData,
    input_grid: Grid,
    primitive: PrimitiveCall,
    param_context: list[ObjectData],
    background_color: int,
) -> ObjectData | None:
    if primitive.op == "delete":
        return None
    if primitive.op == "translate":
        dy = _resolve_numeric_param(primitive.params.get("dy", 0), obj, input_grid, param_context)
        dx = _resolve_numeric_param(primitive.params.get("dx", 0), obj, input_grid, param_context)
        pixels = {(row + dy, col + dx) for row, col in obj.pixels}
        pc = {(row + dy, col + dx): v for (row, col), v in obj.pixel_colors.items()}
        return _replace_pixels(obj, pixels, pc)
    if primitive.op == "rotate":
        quarter_turns = int(primitive.params.get("quarter_turns", 1)) % 4
        pixels = set(obj.pixels)
        pc = dict(obj.pixel_colors)
        for _ in range(quarter_turns):
            pixels, pc = _rotate_once_with_colors(pixels, pc)
        return _replace_pixels(obj, pixels, pc)
    if primitive.op == "flip":
        axis = str(primitive.params.get("axis", "horizontal"))
        new_pixels, new_pc = _flip_pixels_with_colors(obj.pixels, obj.pixel_colors, axis)
        return _replace_pixels(obj, new_pixels, new_pc)
    if primitive.op == "recolor":
        color = int(primitive.params["color"])
        attrs = dict(obj.attrs)
        attrs["color"] = color
        attrs["dominant_color"] = color
        pc = {k: color for k in obj.pixel_colors}
        return replace(obj, attrs=attrs, pixel_colors=pc)
    if primitive.op == "fill":
        mode = str(primitive.params.get("mode", "bbox_holes"))
        color = int(primitive.params.get("color", obj.attrs.get("dominant_color", 0)))
        pixels = _fill_pixels(obj.pixels, mode)
        pc = dict(obj.pixel_colors)
        for cell in pixels:
            if cell not in pc:
                pc[cell] = color
        attrs = dict(obj.attrs)
        attrs["color"] = color
        attrs["dominant_color"] = color
        return _replace_pixels(replace(obj, attrs=attrs), pixels, pc)
    if primitive.op == "crop":
        mode = str(primitive.params.get("mode", "tight_bbox"))
        return _crop_object(obj, input_grid, mode)
    if primitive.op == "extend_to_boundary":
        direction = str(primitive.params.get("direction", "nearest_boundary"))
        pixels = _extend_to_boundary_pixels(obj, direction, input_grid, param_context)
        ext_color = int(obj.attrs.get("dominant_color", 0))
        pc = dict(obj.pixel_colors)
        for cell in pixels:
            if cell not in pc:
                pc[cell] = ext_color
        return _replace_pixels(obj, pixels, pc)
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
        pixel_colors=dict(obj.pixel_colors),
    )


def _replace_pixels(obj: ObjectData, pixels: set[tuple[int, int]], pixel_colors: dict[tuple[int, int], int] | None = None) -> ObjectData:
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
    new_pc = pixel_colors if pixel_colors is not None else {}
    return replace(obj, pixels=pixels, bbox=bbox, attrs=attrs, pixel_colors=new_pc)


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


def _rotate_once_with_colors(
    pixels: set[tuple[int, int]],
    pixel_colors: dict[tuple[int, int], int],
) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]:
    if not pixels:
        return set(), {}
    min_row = min(row for row, _ in pixels)
    min_col = min(col for _, col in pixels)
    max_row = max(row for row, _ in pixels)
    height = max_row - min_row + 1
    new_pixels: set[tuple[int, int]] = set()
    new_pc: dict[tuple[int, int], int] = {}
    for row, col in pixels:
        nr, nc = col - min_col, height - 1 - (row - min_row)
        dest = (nr + min_row, nc + min_col)
        new_pixels.add(dest)
        if (row, col) in pixel_colors:
            new_pc[dest] = pixel_colors[(row, col)]
    return new_pixels, new_pc


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


def _flip_pixels_with_colors(
    pixels: set[tuple[int, int]],
    pixel_colors: dict[tuple[int, int], int],
    axis: str,
) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]:
    if not pixels:
        return set(), {}
    min_row = min(row for row, _ in pixels)
    min_col = min(col for _, col in pixels)
    max_row = max(row for row, _ in pixels)
    max_col = max(col for _, col in pixels)
    new_pixels: set[tuple[int, int]] = set()
    new_pc: dict[tuple[int, int], int] = {}
    for row, col in pixels:
        if axis == "horizontal":
            dest = (row, max_col - (col - min_col))
        elif axis == "vertical":
            dest = (max_row - (row - min_row), col)
        else:
            raise ValueError(f"Unsupported flip axis: {axis}")
        new_pixels.add(dest)
        if (row, col) in pixel_colors:
            new_pc[dest] = pixel_colors[(row, col)]
    return new_pixels, new_pc


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
        pc = {(r - min_row, c - min_col): v for (r, c), v in obj.pixel_colors.items() if (r, c) in obj.pixels}
        cropped = _replace_pixels(obj, pixels, pc)
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
        return _replace_pixels(replace(obj, attrs=attrs), {(0, 0)}, {(0, 0): color})
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
        pc = {(r - min_row, c - min_col): v for (r, c), v in obj.pixel_colors.items() if (r, c) in obj.pixels}
        normalized.append(_replace_pixels(obj, pixels, pc))
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
        pixel_colors={(0, 0): color},
    )
    return ([obj], (center_row, center_col, center_row, center_col))


def _delete_input_center_component(
    objects: list[ObjectData],
    input_grid: Grid,
    target_ids: set[str],
    background_color: int,
) -> list[ObjectData]:
    component_pixels = _input_center_component_pixels(input_grid, background_color)
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
        remaining_pc = {k: v for k, v in obj.pixel_colors.items() if k in remaining_pixels}
        result.append(_replace_pixels(obj, remaining_pixels, remaining_pc))
    return result


def _translate_rare_color_motif_to_largest_component_center(
    objects: list[ObjectData],
    input_grid: Grid,
    target_ids: set[str],
    background_color: int,
) -> list[ObjectData]:
    if not target_ids:
        return [_clone_object(obj) for obj in objects]

    rare_color = _rare_nonzero_color(input_grid, background_color)
    if rare_color is None:
        return [_clone_object(obj) for obj in objects]

    motif_pixels = {
        (row_index, col_index)
        for row_index, row in enumerate(input_grid)
        for col_index, value in enumerate(row)
        if value == rare_color
    }
    anchor_pixels = _largest_nonzero_component_pixels(input_grid, background_color)
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
    if target == "largest_object":
        selected = _select_extreme_object(objects, smallest=False)
        return {selected.id} if selected is not None else set()
    if target == "rare_color_object":
        selected = _select_rare_color_object(objects)
        return {selected.id} if selected is not None else set()
    return set()


def _background_color(input_grid: Grid, input_plan: SegmentationPlan | None = None) -> int:
    if input_plan is not None and input_plan.bg_color is not None:
        return input_plan.bg_color
    return 0


def _rare_nonzero_color(input_grid: Grid, background_color: int) -> int | None:
    color_counts = Counter(
        value
        for row in input_grid
        for value in row
        if value != background_color
    )
    if not color_counts:
        return None
    return min(color_counts, key=lambda color: (color_counts[color], color))


def _largest_nonzero_component_pixels(input_grid: Grid, background_color: int) -> set[tuple[int, int]]:
    if not input_grid or not input_grid[0]:
        return set()

    rows = len(input_grid)
    cols = len(input_grid[0])
    visited: set[tuple[int, int]] = set()
    largest: set[tuple[int, int]] = set()
    for row in range(rows):
        for col in range(cols):
            if input_grid[row][col] == background_color or (row, col) in visited:
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
                    if input_grid[next_row][next_col] == background_color or next_cell in visited:
                        continue
                    visited.add(next_cell)
                    pending.append(next_cell)
            if not largest or _component_sort_key(component) > _component_sort_key(largest):
                largest = component
    return largest


def _input_center_component_pixels(input_grid: Grid, background_color: int) -> set[tuple[int, int]]:
    if not input_grid or not input_grid[0]:
        return set()

    center_row = len(input_grid) // 2
    center_col = len(input_grid[0]) // 2
    center_color = input_grid[center_row][center_col]
    if center_color == background_color:
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


def _extend_to_boundary_pixels(
    obj: ObjectData,
    direction: str,
    input_grid: Grid,
    param_context: list[ObjectData],
) -> set[tuple[int, int]]:
    if direction == "nearest_boundary":
        direction = _nearest_boundary_direction(obj.bbox, input_grid)
    direction_vectors = {
        "up": (-1, 0),
        "down": (1, 0),
        "left": (0, -1),
        "right": (0, 1),
    }
    if direction not in direction_vectors:
        raise ValueError(f"Unsupported extend_to_boundary direction: {direction}")

    delta_row, delta_col = direction_vectors[direction]
    rows = len(input_grid)
    cols = len(input_grid[0]) if input_grid else 0
    other_pixels = {
        pixel
        for other in param_context
        if other.id != obj.id
        for pixel in other.pixels
    }
    extended = set(obj.pixels)
    for row, col in sorted(obj.pixels):
        current_row, current_col = row, col
        while True:
            next_row = current_row + delta_row
            next_col = current_col + delta_col
            if not (0 <= next_row < rows and 0 <= next_col < cols):
                break
            if (next_row, next_col) in other_pixels:
                break
            extended.add((next_row, next_col))
            current_row, current_col = next_row, next_col
    return extended


def _nearest_boundary_direction(bbox: tuple[int, int, int, int], input_grid: Grid) -> str:
    rows = len(input_grid)
    cols = len(input_grid[0]) if input_grid else 0
    min_row, min_col, max_row, max_col = bbox
    distances = [
        (min_row, "up"),
        (rows - 1 - max_row, "down"),
        (min_col, "left"),
        (cols - 1 - max_col, "right"),
    ]
    return min(distances, key=lambda item: (item[0], {"up": 0, "down": 1, "left": 2, "right": 3}[item[1]]))[1]


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
    pc = {(r, c): input_grid[r][c] for r, c in pixels if 0 <= r < len(input_grid) and 0 <= c < len(input_grid[0])}
    replaced = _replace_pixels(obj, pixels, pc)
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
        pixel_colors={cell: color for cell in pixels},
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
