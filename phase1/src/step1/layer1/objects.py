from __future__ import annotations

from collections import Counter, deque

from phase1.src.step1.data.models import Cell, Grid, ObjectData


def extract_cc_objects(grid: Grid, connectivity: int) -> list[set[Cell]]:
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
                    visited.add(next_cell)
                    queue.append(next_cell)
            components.append(component)
    return _sort_components(components)


def build_object(object_id: str, pixels: set[Cell], grid: Grid) -> ObjectData:
    canvas_height = len(grid)
    canvas_width = len(grid[0])
    rows = [row for row, _ in pixels]
    cols = [col for _, col in pixels]
    bbox = (min(rows), min(cols), max(rows), max(cols))
    colors = Counter(grid[row][col] for row, col in pixels)
    dominant_color = sorted(colors.items(), key=lambda item: (-item[1], item[0]))[0][0]
    attrs = {
        "dominant_color": dominant_color,
        "color": dominant_color,
        "area": len(pixels),
        "height": bbox[2] - bbox[0] + 1,
        "width": bbox[3] - bbox[1] + 1,
        "center_row": (bbox[0] + bbox[2]) / 2,
        "center_col": (bbox[1] + bbox[3]) / 2,
        "canvas_height": canvas_height,
        "canvas_width": canvas_width,
    }
    return ObjectData(id=object_id, pixels=set(pixels), bbox=bbox, attrs=attrs)


def build_whole_grid_object(grid: Grid) -> ObjectData:
    rows = len(grid)
    cols = len(grid[0])
    pixels = {(row, col) for row in range(rows) for col in range(cols)}
    colors = Counter(color for row in grid for color in row)
    dominant_color = sorted(colors.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return ObjectData(
        id="whole_grid:0",
        pixels=pixels,
        bbox=(0, 0, rows - 1, cols - 1),
        attrs={
            "dominant_color": dominant_color,
            "color": dominant_color,
            "area": rows * cols,
            "height": rows,
            "width": cols,
            "center_row": (rows - 1) / 2,
            "center_col": (cols - 1) / 2,
            "canvas_height": rows,
            "canvas_width": cols,
        },
    )


def _sort_components(components: list[set[Cell]]) -> list[set[Cell]]:
    def key(component: set[Cell]) -> tuple[tuple[int, int, int, int], tuple[Cell, ...]]:
        rows = [row for row, _ in component]
        cols = [col for _, col in component]
        bbox = (min(rows), min(cols), max(rows), max(cols))
        return (bbox, tuple(sorted(component)))

    return sorted(components, key=key)
