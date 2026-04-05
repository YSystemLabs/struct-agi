from __future__ import annotations

from phase1.src.step2.config import ALLOWED_OUTPUT_SIZE_RULES
from phase1.src.step2.data.models import Grid, ObjectData


def render_objects(
    objects: list[ObjectData],
    background_color: int,
    grid_shape: tuple[int, int],
    program_order: list[str] | None = None,
) -> Grid:
    rows, cols = grid_shape
    grid = [[background_color for _ in range(cols)] for _ in range(rows)]
    order_lookup = {object_id: index for index, object_id in enumerate(program_order or [])}

    def sort_key(item: ObjectData) -> tuple[int, int, str]:
        area = int(item.attrs.get("area", len(item.pixels)))
        priority = order_lookup.get(item.id, -1)
        return (-area, priority, item.id)

    for obj in sorted(objects, key=sort_key):
        default_color = int(obj.attrs.get("color", obj.attrs.get("dominant_color", 0)))
        for row, col in sorted(obj.pixels):
            if 0 <= row < rows and 0 <= col < cols:
                grid[row][col] = obj.pixel_colors.get((row, col), default_color)
    return grid


def infer_output_grid_shape(
    input_grid: Grid,
    objects: list[ObjectData],
    size_rule: str,
    crop_bbox: tuple[int, int, int, int] | None = None,
) -> tuple[int, int]:
    if size_rule not in ALLOWED_OUTPUT_SIZE_RULES:
        raise ValueError(f"Unsupported output size rule for Step 1: {size_rule}")

    if size_rule == "preserve_input_size":
        return (len(input_grid), len(input_grid[0]))

    if size_rule == "crop_center_cell":
        return (1, 1)

    if size_rule == "crop_selected_bbox":
        if crop_bbox is None:
            crop_bbox = _union_bbox(objects)
        if crop_bbox is None:
            return (1, 1)
        min_row, min_col, max_row, max_col = crop_bbox
        return (max_row - min_row + 1, max_col - min_col + 1)

    bbox = _union_bbox(objects)
    if bbox is None:
        return (len(input_grid), len(input_grid[0]))
    min_row, min_col, max_row, max_col = bbox
    return (max_row - min_row + 1, max_col - min_col + 1)


def _union_bbox(objects: list[ObjectData]) -> tuple[int, int, int, int] | None:
    if not objects or all(not obj.pixels for obj in objects):
        return None
    min_row = min(row for obj in objects for row, _ in obj.pixels)
    min_col = min(col for obj in objects for _, col in obj.pixels)
    max_row = max(row for obj in objects for row, _ in obj.pixels)
    max_col = max(col for obj in objects for _, col in obj.pixels)
    return (min_row, min_col, max_row, max_col)
