from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from phase1.src.step2.data.models import Grid, ObjectData  # noqa: E402
from phase1.src.step2.layer4.render import render_objects  # noqa: E402


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, set):
        return [to_jsonable(item) for item in sorted(value)]
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)


def grid_shape(grid: Grid) -> tuple[int, int]:
    return (len(grid), len(grid[0]) if grid else 0)


def clone_grid(grid: Grid) -> Grid:
    return [row[:] for row in grid]


def exact_match(left: Grid, right: Grid) -> bool:
    return left == right


def pixel_accuracy(predicted: Grid, expected: Grid) -> float:
    if not expected or not expected[0]:
        return 1.0 if predicted == expected else 0.0
    if grid_shape(predicted) != grid_shape(expected):
        return 0.0
    rows, cols = grid_shape(expected)
    correct = 0
    total = rows * cols
    for row in range(rows):
        for col in range(cols):
            if predicted[row][col] == expected[row][col]:
                correct += 1
    return correct / total if total else 1.0


def color_frequencies(grid: Grid) -> Counter[int]:
    return Counter(value for row in grid for value in row)


def resolve_background_color(grid: Grid, mode: str) -> int | None:
    if mode == "no_fixed_background":
        return None
    counts = color_frequencies(grid)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if not ranked:
        return 0
    if mode == "top1":
        return ranked[0][0]
    if mode == "top2":
        return ranked[1][0] if len(ranked) > 1 else ranked[0][0]
    raise ValueError(f"Unsupported background mode: {mode}")


def foreground_cells(grid: Grid, background_color: int | None) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for row, values in enumerate(grid):
        for col, value in enumerate(values):
            if background_color is None:
                if value != 0:
                    cells.append((row, col))
            elif value != background_color:
                cells.append((row, col))
    return cells


def bbox_from_pixels(pixels: set[tuple[int, int]]) -> tuple[int, int, int, int] | None:
    if not pixels:
        return None
    rows = [row for row, _ in pixels]
    cols = [col for _, col in pixels]
    return (min(rows), min(cols), max(rows), max(cols))


def normalize_pixels(pixels: set[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    if not pixels:
        return ()
    min_row = min(row for row, _ in pixels)
    min_col = min(col for _, col in pixels)
    return tuple(sorted((row - min_row, col - min_col) for row, col in pixels))


def crop_grid(grid: Grid, bbox: tuple[int, int, int, int]) -> Grid:
    min_row, min_col, max_row, max_col = bbox
    return [row[min_col : max_col + 1] for row in grid[min_row : max_row + 1]]


def pad_grid(grid: Grid, pad: int, color: int) -> Grid:
    rows, cols = grid_shape(grid)
    padded_rows = rows + 2 * pad
    padded_cols = cols + 2 * pad
    result = [[color for _ in range(padded_cols)] for _ in range(padded_rows)]
    for row in range(rows):
        for col in range(cols):
            result[row + pad][col + pad] = grid[row][col]
    return result


def shift_grid(grid: Grid, dx: int, dy: int, fill_color: int, pad_if_needed: bool = False) -> Grid:
    rows, cols = grid_shape(grid)
    working = clone_grid(grid)
    row_offset = 0
    col_offset = 0
    if pad_if_needed:
        touches_edge = False
        for row in range(rows):
            for col in range(cols):
                if working[row][col] == fill_color:
                    continue
                next_row = row + dy
                next_col = col + dx
                if not (0 <= next_row < rows and 0 <= next_col < cols):
                    touches_edge = True
                    break
            if touches_edge:
                break
        if touches_edge:
            working = pad_grid(working, 1, fill_color)
            row_offset = 1
            col_offset = 1
            rows, cols = grid_shape(working)
    result = [[fill_color for _ in range(cols)] for _ in range(rows)]
    for row in range(rows):
        for col in range(cols):
            value = working[row][col]
            if value == fill_color:
                continue
            next_row = row + dy + row_offset
            next_col = col + dx + col_offset
            if 0 <= next_row < rows and 0 <= next_col < cols:
                result[next_row][next_col] = value
    return result


def most_common_non_background(pixel_colors: dict[tuple[int, int], int], fallback: int = 0) -> int:
    if not pixel_colors:
        return fallback
    non_zero = Counter(value for value in pixel_colors.values() if value != 0)
    if non_zero:
        return sorted(non_zero.items(), key=lambda item: (-item[1], item[0]))[0][0]
    full = Counter(pixel_colors.values())
    return sorted(full.items(), key=lambda item: (-item[1], item[0]))[0][0]


def make_object(object_id: str, pixels: set[tuple[int, int]], grid: Grid) -> ObjectData:
    bbox = bbox_from_pixels(pixels)
    if bbox is None:
        raise ValueError("Object pixels cannot be empty")
    rows, cols = grid_shape(grid)
    pixel_colors = {cell: grid[cell[0]][cell[1]] for cell in pixels}
    dominant_color = most_common_non_background(pixel_colors)
    min_row, min_col, max_row, max_col = bbox
    attrs = {
        "dominant_color": dominant_color,
        "color": dominant_color,
        "area": len(pixels),
        "height": max_row - min_row + 1,
        "width": max_col - min_col + 1,
        "center_row": (min_row + max_row) / 2,
        "center_col": (min_col + max_col) / 2,
        "canvas_height": rows,
        "canvas_width": cols,
    }
    return ObjectData(
        id=object_id,
        pixels=set(pixels),
        bbox=bbox,
        attrs=attrs,
        pixel_colors=pixel_colors,
    )


def make_bbox_object(object_id: str, support_pixels: set[tuple[int, int]], grid: Grid) -> ObjectData:
    bbox = bbox_from_pixels(support_pixels)
    if bbox is None:
        raise ValueError("Support pixels cannot be empty")
    min_row, min_col, max_row, max_col = bbox
    pixels = {(row, col) for row in range(min_row, max_row + 1) for col in range(min_col, max_col + 1)}
    return make_object(object_id, pixels, grid)


def clone_object(obj: ObjectData) -> ObjectData:
    return ObjectData(
        id=obj.id,
        pixels=set(obj.pixels),
        bbox=tuple(obj.bbox),
        attrs=dict(obj.attrs),
        pixel_colors=dict(obj.pixel_colors),
    )


def replace_object_pixels(
    obj: ObjectData,
    pixels: set[tuple[int, int]],
    pixel_colors: dict[tuple[int, int], int],
) -> ObjectData:
    bbox = bbox_from_pixels(pixels)
    if bbox is None:
        bbox = (0, 0, 0, 0)
    attrs = dict(obj.attrs)
    attrs["area"] = len(pixels)
    attrs["height"] = bbox[2] - bbox[0] + 1 if pixels else 0
    attrs["width"] = bbox[3] - bbox[1] + 1 if pixels else 0
    attrs["center_row"] = (bbox[0] + bbox[2]) / 2 if pixels else 0.0
    attrs["center_col"] = (bbox[1] + bbox[3]) / 2 if pixels else 0.0
    if pixels:
        attrs["dominant_color"] = most_common_non_background(pixel_colors, int(attrs.get("dominant_color", 0)))
        attrs["color"] = attrs["dominant_color"]
    return ObjectData(
        id=obj.id,
        pixels=set(pixels),
        bbox=bbox,
        attrs=attrs,
        pixel_colors=dict(pixel_colors),
    )


def object_crop_grid(obj: ObjectData, background_color: int = 0) -> Grid:
    min_row, min_col, max_row, max_col = obj.bbox
    rows = max_row - min_row + 1
    cols = max_col - min_col + 1
    grid = [[background_color for _ in range(cols)] for _ in range(rows)]
    for (row, col), color in obj.pixel_colors.items():
        if row < min_row or row > max_row or col < min_col or col > max_col:
            continue
        grid[row - min_row][col - min_col] = color
    return grid


def render_object_list(
    objects: list[ObjectData],
    background_color: int,
    shape: tuple[int, int],
) -> Grid:
    return render_objects(objects, background_color, shape)
