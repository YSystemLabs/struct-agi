from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from itertools import permutations


Grid = list[list[int]]
Cell = tuple[int, int]
RelationEdge = tuple[str, str, str]


@dataclass(frozen=True)
class ObjectData:
    id: str
    pixels: set[Cell]
    bbox: tuple[int, int, int, int]
    attrs: dict[str, int | float]
    pixel_colors: dict[Cell, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SegmentationPlan:
    plan_id: str
    method: str
    objects: list[ObjectData]
    relations: list[RelationEdge]
    bg_color: int | None = None


def extract_cc_objects(grid: Grid, connectivity: int, same_color: bool = False) -> list[set[Cell]]:
    if connectivity not in {4, 8}:
        raise ValueError("connectivity must be 4 or 8")

    visited: set[Cell] = set()
    components: list[set[Cell]] = []
    rows = len(grid)
    cols = len(grid[0])
    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if connectivity == 8:
        neighbors.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])

    for row in range(rows):
        for col in range(cols):
            if grid[row][col] == 0 or (row, col) in visited:
                continue
            component: set[Cell] = set()
            seed_color = grid[row][col]
            queue: deque[Cell] = deque([(row, col)])
            visited.add((row, col))
            while queue:
                current_row, current_col = queue.popleft()
                component.add((current_row, current_col))
                for delta_row, delta_col in neighbors:
                    next_row = current_row + delta_row
                    next_col = current_col + delta_col
                    next_cell = (next_row, next_col)
                    if not (0 <= next_row < rows and 0 <= next_col < cols):
                        continue
                    if grid[next_row][next_col] == 0 or next_cell in visited:
                        continue
                    if same_color and grid[next_row][next_col] != seed_color:
                        continue
                    visited.add(next_cell)
                    queue.append(next_cell)
            components.append(component)
    return _sort_components(components)


def extract_relations(objects: list[ObjectData]) -> list[RelationEdge]:
    relations: set[RelationEdge] = set()
    for source, target in permutations(objects, 2):
        relation = _relative_position(source, target)
        if relation is not None:
            relations.add((source.id, target.id, relation))
        for alignment in _alignment_relations(source, target):
            relations.add((source.id, target.id, alignment))
        if _are_adjacent(source, target):
            relations.add((source.id, target.id, "adjacency"))
        if _contains(source, target):
            relations.add((source.id, target.id, "containment"))
    return sorted(relations)


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


def _sort_components(components: list[set[Cell]]) -> list[set[Cell]]:
    def key(component: set[Cell]) -> tuple[tuple[int, int, int, int], tuple[Cell, ...]]:
        rows = [row for row, _ in component]
        cols = [col for _, col in component]
        bbox = (min(rows), min(cols), max(rows), max(cols))
        return (bbox, tuple(sorted(component)))

    return sorted(components, key=key)


def _relative_position(source: ObjectData, target: ObjectData) -> str | None:
    source_row = float(source.attrs["center_row"])
    source_col = float(source.attrs["center_col"])
    target_row = float(target.attrs["center_row"])
    target_col = float(target.attrs["center_col"])
    row_gap = target_row - source_row
    col_gap = target_col - source_col
    if abs(col_gap) >= abs(row_gap) and col_gap > 0:
        return "left_of"
    if abs(col_gap) >= abs(row_gap) and col_gap < 0:
        return "right_of"
    if row_gap > 0:
        return "above"
    if row_gap < 0:
        return "below"
    return None


def _alignment_relations(source: ObjectData, target: ObjectData) -> list[str]:
    relations: list[str] = []
    if source.bbox[0] == target.bbox[0]:
        relations.append("aligned_top")
    if source.bbox[2] == target.bbox[2]:
        relations.append("aligned_bottom")
    if source.bbox[1] == target.bbox[1]:
        relations.append("aligned_left")
    if source.bbox[3] == target.bbox[3]:
        relations.append("aligned_right")
    if source.attrs["center_row"] == target.attrs["center_row"]:
        relations.append("aligned_row_center")
    if source.attrs["center_col"] == target.attrs["center_col"]:
        relations.append("aligned_col_center")
    return relations


def _are_adjacent(source: ObjectData, target: ObjectData) -> bool:
    target_pixels = target.pixels
    for row, col in source.pixels:
        for delta_row, delta_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if (row + delta_row, col + delta_col) in target_pixels:
                return True
    return False


def _contains(source: ObjectData, target: ObjectData) -> bool:
    return (
        source.bbox[0] >= target.bbox[0]
        and source.bbox[1] >= target.bbox[1]
        and source.bbox[2] <= target.bbox[2]
        and source.bbox[3] <= target.bbox[3]
    )