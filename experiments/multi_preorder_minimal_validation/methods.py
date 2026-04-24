from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from itertools import combinations, product
from statistics import median
from typing import Any

from common import (
    Grid,
    ObjectData,
    bbox_from_pixels,
    color_frequencies,
    foreground_cells,
    grid_shape,
    make_bbox_object,
    make_object,
    normalize_pixels,
    resolve_background_color,
)
from configs import AppendixBConfig, PrimaryTaskEntry
from phase1.src.step2.data.models import SegmentationPlan
from phase1.src.step2.layer1.objects import extract_cc_objects
from phase1.src.step2.layer1.relations import extract_relations


DIRECTIONS_4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIRECTIONS_8 = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)
ROLE_ORDER = (
    "background",
    "unique_non_background",
    "dominant_non_background",
    "second_non_background",
)


@dataclass(frozen=True)
class MethodHypothesis:
    method_name: str
    bg_mode: str
    r: int
    theta: float | None
    weight_id: str
    feature_subset_id: str
    preorder_profile_id: str

    @property
    def plan_id(self) -> str:
        theta_text = "na" if self.theta is None else str(self.theta)
        return ":".join(
            (
                self.method_name,
                self.bg_mode,
                f"r{self.r}",
                f"theta{theta_text}",
                self.weight_id,
                self.feature_subset_id,
                self.preorder_profile_id,
            )
        )


@dataclass
class PairContext:
    pair_index: int
    input_grid: Grid
    output_grid: Grid
    hypothesis: MethodHypothesis
    plan: SegmentationPlan
    bg_color: int
    color_roles: dict[str, int | None]
    relation_signature_cache: dict[str, tuple[tuple[str, int], ...]] = field(default_factory=dict)
    selector_cache: dict[str, ObjectData | None] = field(default_factory=dict)


def build_method_hypotheses(config: AppendixBConfig, method_name: str) -> list[MethodHypothesis]:
    radii = [int(value) for value in config.global_constants["neighborhood_radii"]]
    background_modes = [str(value) for value in config.global_constants["background_modes"]]
    thetas = [float(value) for value in config.global_constants["theta_candidates"]]
    weight_ids = sorted(config.weight_grid)

    if method_name in {"cc4", "cc8"}:
        return [
            MethodHypothesis(
                method_name=method_name,
                bg_mode="top1",
                r=1,
                theta=None,
                weight_id=method_name,
                feature_subset_id=f"baseline:{method_name}",
                preorder_profile_id=f"baseline:{method_name}",
            )
        ]
    if method_name == "bbox":
        return [
            MethodHypothesis(
                method_name=method_name,
                bg_mode=bg_mode,
                r=1,
                theta=None,
                weight_id="bbox",
                feature_subset_id="baseline:bbox_rectangles",
                preorder_profile_id=f"baseline:bbox:{bg_mode}",
            )
            for bg_mode in background_modes
        ]
    if method_name == "raw_local_feature_clustering":
        return [
            MethodHypothesis(
                method_name=method_name,
                bg_mode=bg_mode,
                r=radius,
                theta=1.0,
                weight_id="raw_exact",
                feature_subset_id="features:raw_full8",
                preorder_profile_id=f"baseline:raw_exact:r{radius}:{bg_mode}",
            )
            for bg_mode, radius in product(background_modes, radii)
        ]
    if method_name == "multi_preorder":
        return [
            MethodHypothesis(
                method_name=method_name,
                bg_mode=bg_mode,
                r=radius,
                theta=theta,
                weight_id=weight_id,
                feature_subset_id="features:full8",
                preorder_profile_id="preorders:config_default",
            )
            for bg_mode, radius, theta, weight_id in product(background_modes, radii, thetas, weight_ids)
        ]
    raise ValueError(f"Unsupported comparison method: {method_name}")


def build_pair_context(
    pair_index: int,
    input_grid: Grid,
    output_grid: Grid,
    hypothesis: MethodHypothesis,
    config: AppendixBConfig,
) -> PairContext:
    plan = build_plan(input_grid, hypothesis, config)
    bg_color = plan.bg_color if plan.bg_color is not None else 0
    return PairContext(
        pair_index=pair_index,
        input_grid=input_grid,
        output_grid=output_grid,
        hypothesis=hypothesis,
        plan=plan,
        bg_color=bg_color,
        color_roles=resolve_color_roles(input_grid, plan.bg_color, plan.objects),
    )


def build_plan(grid: Grid, hypothesis: MethodHypothesis, config: AppendixBConfig) -> SegmentationPlan:
    if hypothesis.method_name == "cc4":
        return _build_cc_plan(grid, connectivity=4)
    if hypothesis.method_name == "cc8":
        return _build_cc_plan(grid, connectivity=8)
    if hypothesis.method_name == "bbox":
        return _build_bbox_plan(grid, hypothesis.bg_mode)
    if hypothesis.method_name == "raw_local_feature_clustering":
        return _build_feature_cluster_plan(grid, hypothesis, config, exact_match_only=True)
    if hypothesis.method_name == "multi_preorder":
        return _build_feature_cluster_plan(grid, hypothesis, config, exact_match_only=False)
    raise ValueError(f"Unsupported method: {hypothesis.method_name}")


def build_h_norm(contexts: list[PairContext], candidate_hypothesis: MethodHypothesis, config: AppendixBConfig) -> tuple[Any, ...]:
    object_counts = [len(context.plan.objects) for context in contexts]
    edge_counts = [count_whitelisted_edges(context.plan.relations) for context in contexts]
    obj_bucket = bucketize_value(int(round(median(object_counts))), config.signature["bucketization"]["obj_count_bucket"])
    edge_bucket = bucketize_value(int(round(median(edge_counts))), config.signature["bucketization"]["edge_count_bucket"])
    field_values = {
        "bg_mode": candidate_hypothesis.bg_mode,
        "r": candidate_hypothesis.r,
        "feature_subset_id": candidate_hypothesis.feature_subset_id,
        "preorder_profile_id": candidate_hypothesis.preorder_profile_id,
        "theta": candidate_hypothesis.theta,
        "weight_id": candidate_hypothesis.weight_id,
        "obj_count_bucket": obj_bucket,
        "edge_count_bucket": edge_bucket,
    }
    return tuple(field_values[field] for field in config.signature["h_norm_fields"])


def count_whitelisted_edges(relations: list[tuple[str, str, str]]) -> int:
    return sum(1 for _, _, relation in relations if relation == "adjacency" or relation == "containment" or relation == "repeat" or relation.startswith("aligned_"))


def select_object(context: PairContext, selector: str) -> ObjectData | None:
    cached = context.selector_cache.get(selector)
    if selector in context.selector_cache:
        return cached
    selected: ObjectData | None = None
    objects = list(context.plan.objects)
    if selector == "largest_object":
        selected = max(objects, key=lambda obj: (int(obj.attrs.get("area", 0)), tuple(-value for value in obj.bbox), obj.id), default=None)
    elif selector == "smallest_object":
        selected = min(objects, key=lambda obj: (int(obj.attrs.get("area", 0)), obj.bbox, obj.id), default=None)
    elif selector == "center_object":
        selected = _select_center_object(objects, context.input_grid)
    elif selector == "boundary_touching_object":
        touching = [obj for obj in objects if boundary_touch_count(obj) > 0]
        selected = max(touching, key=lambda obj: (boundary_touch_count(obj), int(obj.attrs.get("area", 0)), tuple(-value for value in obj.bbox), obj.id), default=None)
    elif selector == "unique_role_color_object":
        selected = _select_unique_role_color_object(objects)
    elif selector == "unique_relation_defined_object":
        selected = _select_unique_relation_defined_object(context, objects)
    else:
        raise ValueError(f"Unsupported selector: {selector}")
    context.selector_cache[selector] = selected
    return selected


def dominant_color_role(obj: ObjectData, context: PairContext) -> str | None:
    color = int(obj.attrs.get("dominant_color", 0))
    for role in ROLE_ORDER:
        if context.color_roles.get(role) == color:
            return role
    return None


def recolor_source_role(obj: ObjectData, context: PairContext) -> str:
    role = dominant_color_role(obj, context)
    if role is not None:
        return role
    return "other_non_background"


def resolve_color_roles(
    grid: Grid,
    background_color: int | None,
    objects: list[ObjectData] | None = None,
) -> dict[str, int | None]:
    counts = color_frequencies(grid)
    if background_color is not None:
        counts.pop(background_color, None)
    else:
        counts.pop(0, None)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    unique_non_background = ranked[0][0] if len(ranked) == 1 else None
    largest_object_color = None
    if objects:
        largest_object = max(
            objects,
            key=lambda obj: (int(obj.attrs.get("area", 0)), tuple(-value for value in obj.bbox), obj.id),
            default=None,
        )
        if largest_object is not None:
            largest_object_color = int(largest_object.attrs.get("dominant_color", 0))
    return {
        "background": background_color if background_color is not None else 0,
        "dominant_non_background": ranked[0][0] if ranked else None,
        "second_non_background": ranked[1][0] if len(ranked) > 1 else None,
        "unique_non_background": unique_non_background,
        "largest_object_color": largest_object_color,
    }


def resolve_role_color(role: str, context: PairContext) -> int | None:
    return context.color_roles.get(role)


def task_gate_summary(task: dict[str, Any], entry: PrimaryTaskEntry) -> dict[str, Any]:
    observed_labels = [classify_pair(pair["input"], pair["output"]) for pair in task["train"]]
    same_size = all(grid_shape(pair["input"]) == grid_shape(pair["output"]) for pair in task["train"])
    return {
        "task_id": entry.task_id,
        "expected_label": entry.observed_label,
        "observed_labels": observed_labels,
        "label_consistent": len(set(observed_labels)) == 1,
        "label_matches_entry": len(set(observed_labels)) == 1 and observed_labels[0] == entry.observed_label,
        "same_input_output_size": same_size,
        "train_pair_count_matches": len(task["train"]) == entry.train_pairs,
    }


def classify_pair(input_grid: Grid, output_grid: Grid) -> str | None:
    if input_grid == output_grid:
        return "identity"
    input_components = _components_by_color(input_grid)
    output_components = _components_by_color(output_grid)
    for _, cells in input_components:
        bbox = bbox_from_pixels(set(cells))
        if bbox is not None and _crop_region(input_grid, bbox) == output_grid:
            return "crop_selected_bbox"
    if grid_shape(input_grid) != grid_shape(output_grid):
        return None
    for _, cells in input_components:
        if _grid_without_component(input_grid, set(cells)) == output_grid:
            return "single_object_delete"
    translation = infer_single_object_translation(input_grid, output_grid)
    if translation is not None:
        return "single_object_translate"
    for input_color, input_cells in input_components:
        input_shape = _shape_signature(input_cells)
        for output_color, output_cells in output_components:
            if _shape_signature(output_cells) != input_shape:
                continue
            input_bbox = bbox_from_pixels(set(input_cells))
            output_bbox = bbox_from_pixels(set(output_cells))
            if input_bbox is None or output_bbox is None:
                continue
            dy = output_bbox[0] - input_bbox[0]
            dx = output_bbox[1] - input_bbox[1]
            if dx == 0 and dy == 0 and input_color != output_color:
                recolored = _replace_component(input_grid, set(input_cells), set(input_cells), output_color)
                if recolored == output_grid:
                    return "single_object_recolor"
    return None


def infer_single_object_translation(input_grid: Grid, output_grid: Grid) -> tuple[int, int] | None:
    if grid_shape(input_grid) != grid_shape(output_grid):
        return None
    input_components = _components_by_color(input_grid)
    output_components = _components_by_color(output_grid)
    for input_color, input_cells in input_components:
        input_shape = _shape_signature(input_cells)
        for output_color, output_cells in output_components:
            if output_color != input_color or _shape_signature(output_cells) != input_shape:
                continue
            input_bbox = bbox_from_pixels(set(input_cells))
            output_bbox = bbox_from_pixels(set(output_cells))
            if input_bbox is None or output_bbox is None:
                continue
            dy = output_bbox[0] - input_bbox[0]
            dx = output_bbox[1] - input_bbox[1]
            shifted = {(row + dy, col + dx) for row, col in input_cells}
            if shifted != set(output_cells):
                continue
            translated = _replace_component(input_grid, set(input_cells), shifted, input_color)
            if translated == output_grid and (dx != 0 or dy != 0):
                return (dx, dy)
    return None


def boundary_touch_count(obj: ObjectData) -> int:
    canvas_height = int(obj.attrs.get("canvas_height", 0))
    canvas_width = int(obj.attrs.get("canvas_width", 0))
    min_row, min_col, max_row, max_col = obj.bbox
    return sum(
        (
            min_row == 0,
            min_col == 0,
            max_row == canvas_height - 1,
            max_col == canvas_width - 1,
        )
    )


def nearest_object_offsets(obj: ObjectData, objects: list[ObjectData]) -> tuple[int, int] | None:
    others = [other for other in objects if other.id != obj.id]
    if not others:
        return None
    chosen = nearest_object_mover(objects)
    if chosen is None or chosen.id != obj.id:
        return None
    best: tuple[tuple[int, int, int, str], tuple[int, int]] | None = None
    min_row, min_col, max_row, max_col = obj.bbox
    for other in others:
        other_min_row, other_min_col, other_max_row, other_max_col = other.bbox
        candidates: list[tuple[int, int]] = []
        if overlap_1d(min_row, max_row, other_min_row, other_max_row):
            candidates.append((other_min_col - max_col - 1, 0))
            candidates.append((other_max_col - min_col + 1, 0))
        if overlap_1d(min_col, max_col, other_min_col, other_max_col):
            candidates.append((0, other_min_row - max_row - 1))
            candidates.append((0, other_max_row - min_row + 1))
        if not candidates:
            candidates.extend(
                [
                    (other_min_col - max_col - 1, other_min_row - max_row - 1),
                    (other_min_col - max_col - 1, other_max_row - min_row + 1),
                    (other_max_col - min_col + 1, other_min_row - max_row - 1),
                    (other_max_col - min_col + 1, other_max_row - min_row + 1),
                ]
            )
        for dx, dy in candidates:
            score = (abs(dx) + abs(dy), abs(dy), abs(dx), other.id)
            if best is None or score < best[0]:
                best = (score, (dx, dy))
    return best[1] if best is not None else None


def boundary_offsets(obj: ObjectData, objects: list[ObjectData], input_grid: Grid) -> tuple[int, int]:
    rows, cols = grid_shape(input_grid)
    direction = boundary_direction(obj, objects, input_grid)
    min_row, min_col, max_row, max_col = obj.bbox
    if direction == "up":
        return (0, -min_row)
    if direction == "down":
        return (0, rows - 1 - max_row)
    if direction == "left":
        return (-min_col, 0)
    return (cols - 1 - max_col, 0)


def bucketize_value(value: int, buckets: list[dict[str, Any]]) -> str:
    for bucket in buckets:
        minimum = int(bucket["min"])
        maximum = bucket["max"]
        if maximum is None and value >= minimum:
            return str(bucket["label"])
        if maximum is not None and minimum <= value <= int(maximum):
            return str(bucket["label"])
    return str(value)


def _build_cc_plan(grid: Grid, connectivity: int) -> SegmentationPlan:
    components = extract_cc_objects(grid, connectivity)
    objects = [make_object(f"cc{connectivity}:{index}", component, grid) for index, component in enumerate(components)]
    return SegmentationPlan(
        plan_id=f"cc{connectivity}",
        method=f"cc{connectivity}",
        objects=objects,
        relations=_augment_relations(objects),
        bg_color=None,
    )


def _build_bbox_plan(grid: Grid, bg_mode: str) -> SegmentationPlan:
    background_color = resolve_background_color(grid, bg_mode)
    masked_grid = [[0 if _is_background(value, background_color) else value for value in row] for row in grid]
    components = extract_cc_objects(masked_grid, 4, same_color=True)
    objects = [make_bbox_object(f"bbox:{index}", component, grid) for index, component in enumerate(components)]
    return SegmentationPlan(
        plan_id=f"bbox:{bg_mode}",
        method="bbox",
        objects=objects,
        relations=_augment_relations(objects),
        bg_color=background_color,
    )


def _build_feature_cluster_plan(
    grid: Grid,
    hypothesis: MethodHypothesis,
    config: AppendixBConfig,
    exact_match_only: bool,
) -> SegmentationPlan:
    background_color = resolve_background_color(grid, hypothesis.bg_mode)
    cells = foreground_cells(grid, background_color)
    feature_vectors = {cell: _compute_cell_features(grid, cell, background_color, hypothesis.r, config) for cell in cells}
    components = _cluster_feature_cells(grid, cells, feature_vectors, hypothesis, config, exact_match_only)
    components = _merge_adjacent_same_color_components(grid, components)
    objects = [make_object(f"{hypothesis.method_name}:{index}", component, grid) for index, component in enumerate(components)]
    return SegmentationPlan(
        plan_id=hypothesis.plan_id,
        method=hypothesis.method_name,
        objects=objects,
        relations=_augment_relations(objects),
        bg_color=background_color,
    )


def _cluster_feature_cells(
    grid: Grid,
    cells: list[tuple[int, int]],
    feature_vectors: dict[tuple[int, int], dict[str, Any]],
    hypothesis: MethodHypothesis,
    config: AppendixBConfig,
    exact_match_only: bool,
) -> list[set[tuple[int, int]]]:
    cell_set = set(cells)
    visited: set[tuple[int, int]] = set()
    components: list[set[tuple[int, int]]] = []
    weight_vector = config.weight_grid.get(hypothesis.weight_id, ())
    for cell in sorted(cells):
        if cell in visited:
            continue
        component: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([cell])
        visited.add(cell)
        while queue:
            current = queue.popleft()
            component.add(current)
            row, col = current
            for delta_row, delta_col in DIRECTIONS_4:
                neighbor = (row + delta_row, col + delta_col)
                if neighbor not in cell_set or neighbor in visited:
                    continue
                if _cell_color(grid, current) != _cell_color(grid, neighbor):
                    continue
                if exact_match_only:
                    matched = _raw_feature_key(feature_vectors[current]) == _raw_feature_key(feature_vectors[neighbor])
                else:
                    matched = _feature_similarity(feature_vectors[current], feature_vectors[neighbor], config, weight_vector) >= float(hypothesis.theta or 0.0)
                if matched:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return sorted(components, key=lambda component: (bbox_from_pixels(component), tuple(sorted(component))))


def _compute_cell_features(
    grid: Grid,
    cell: tuple[int, int],
    background_color: int | None,
    radius: int,
    config: AppendixBConfig,
) -> dict[str, Any]:
    row, col = cell
    rows, cols = grid_shape(grid)
    center_color = grid[row][col]
    feature_values: dict[str, Any] = {}
    for feature in config.features:
        feature_id = str(feature["id"])
        if feature_id == "same8":
            feature_values[feature_id] = _directional_mask(grid, cell, radius, lambda value: value == center_color)
        elif feature_id == "bg8":
            feature_values[feature_id] = _directional_mask(grid, cell, radius, lambda value: background_color is not None and value == background_color)
        elif feature_id == "run_up":
            feature_values[feature_id] = _run_length(grid, row, col, -1, 0)
        elif feature_id == "run_down":
            feature_values[feature_id] = _run_length(grid, row, col, 1, 0)
        elif feature_id == "run_left":
            feature_values[feature_id] = _run_length(grid, row, col, 0, -1)
        elif feature_id == "run_right":
            feature_values[feature_id] = _run_length(grid, row, col, 0, 1)
        elif feature_id == "trans":
            feature_values[feature_id] = _transition_count(grid, cell, radius)
        elif feature_id == "bdist":
            feature_values[feature_id] = min(row, col, rows - 1 - row, cols - 1 - col)
        else:
            raise ValueError(f"Unsupported feature id: {feature_id}")
    return feature_values


def _feature_similarity(
    left: dict[str, Any],
    right: dict[str, Any],
    config: AppendixBConfig,
    weight_vector: tuple[float, ...],
) -> float:
    weights = list(weight_vector) if weight_vector else [1.0 / len(config.features)] * len(config.features)
    total = 0.0
    for weight, feature in zip(weights, config.features):
        feature_id = str(feature["id"])
        preorder_type = str(feature["preorder_type"])
        if preorder_type == "subset":
            total += weight * _subset_similarity(int(left[feature_id]), int(right[feature_id]))
        elif preorder_type in {"natural", "reverse_natural"}:
            total += weight * _bucket_similarity(left[feature_id], right[feature_id], config.rank_buckets)
        else:
            total += weight * (1.0 if left[feature_id] == right[feature_id] else 0.0)
    return total


def _raw_feature_key(features: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(features.items()))


def _subset_similarity(left_mask: int, right_mask: int) -> float:
    left_bits = left_mask.bit_count()
    right_bits = right_mask.bit_count()
    if left_bits == 0 and right_bits == 0:
        return 1.0
    common = (left_mask & right_mask).bit_count()
    return common / max(left_bits, right_bits, 1)


def _bucket_similarity(left_value: int, right_value: int, rank_buckets: tuple[dict[str, Any], ...]) -> float:
    left_index = _bucket_index(left_value, rank_buckets)
    right_index = _bucket_index(right_value, rank_buckets)
    return 1.0 / (1.0 + abs(left_index - right_index))


def _bucket_index(value: int, rank_buckets: tuple[dict[str, Any], ...]) -> int:
    for index, bucket in enumerate(rank_buckets):
        minimum = int(bucket["min"])
        maximum = bucket["max"]
        if maximum is None and value >= minimum:
            return index
        if maximum is not None and minimum <= value <= int(maximum):
            return index
    return len(rank_buckets) - 1


def _directional_mask(
    grid: Grid,
    cell: tuple[int, int],
    radius: int,
    predicate: Any,
) -> int:
    rows, cols = grid_shape(grid)
    row, col = cell
    mask = 0
    for index, (delta_row, delta_col) in enumerate(DIRECTIONS_8):
        matched = False
        for step in range(1, radius + 1):
            next_row = row + delta_row * step
            next_col = col + delta_col * step
            if not (0 <= next_row < rows and 0 <= next_col < cols):
                break
            if predicate(grid[next_row][next_col]):
                matched = True
                break
        if matched:
            mask |= 1 << index
    return mask


def _cell_color(grid: Grid, cell: tuple[int, int]) -> int:
    return grid[cell[0]][cell[1]]


def _merge_adjacent_same_color_components(
    grid: Grid,
    components: list[set[tuple[int, int]]],
) -> list[set[tuple[int, int]]]:
    if len(components) < 2:
        return components
    parent = list(range(len(components)))
    cell_to_component = {
        cell: index
        for index, component in enumerate(components)
        for cell in component
    }

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for index, component in enumerate(components):
        for row, col in component:
            color = _cell_color(grid, (row, col))
            for delta_row, delta_col in DIRECTIONS_4:
                neighbor = (row + delta_row, col + delta_col)
                neighbor_index = cell_to_component.get(neighbor)
                if neighbor_index is None or neighbor_index == index:
                    continue
                if _cell_color(grid, neighbor) == color:
                    union(index, neighbor_index)

    merged: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for index, component in enumerate(components):
        merged[find(index)].update(component)
    return sorted(merged.values(), key=lambda component: (bbox_from_pixels(component), tuple(sorted(component))))


def _run_length(grid: Grid, row: int, col: int, delta_row: int, delta_col: int) -> int:
    rows, cols = grid_shape(grid)
    color = grid[row][col]
    count = 0
    next_row = row + delta_row
    next_col = col + delta_col
    while 0 <= next_row < rows and 0 <= next_col < cols and grid[next_row][next_col] == color:
        count += 1
        next_row += delta_row
        next_col += delta_col
    return count


def _transition_count(grid: Grid, cell: tuple[int, int], radius: int) -> int:
    rows, cols = grid_shape(grid)
    row, col = cell
    color = grid[row][col]
    count = 0
    for delta_row, delta_col in DIRECTIONS_8:
        next_row = row + delta_row * min(radius, 1)
        next_col = col + delta_col * min(radius, 1)
        if not (0 <= next_row < rows and 0 <= next_col < cols):
            continue
        if grid[next_row][next_col] != color:
            count += 1
    return count


def _augment_relations(objects: list[ObjectData]) -> list[tuple[str, str, str]]:
    relations = set(extract_relations(objects))
    repeat_groups: dict[tuple[tuple[int, int], ...], list[ObjectData]] = defaultdict(list)
    for obj in objects:
        repeat_groups[normalize_pixels(obj.pixels)].append(obj)
    for group in repeat_groups.values():
        if len(group) < 2:
            continue
        for source, target in combinations(group, 2):
            relations.add((source.id, target.id, "repeat"))
            relations.add((target.id, source.id, "repeat"))
    return sorted(relations)


def _select_center_object(objects: list[ObjectData], input_grid: Grid) -> ObjectData | None:
    if not objects or not input_grid:
        return None
    center_row = (len(input_grid) - 1) / 2
    center_col = (len(input_grid[0]) - 1) / 2
    return min(
        objects,
        key=lambda obj: (
            min(abs(row - center_row) + abs(col - center_col) for row, col in obj.pixels),
            int(obj.attrs.get("area", 0)),
            obj.bbox,
            obj.id,
        ),
    )


def _select_unique_role_color_object(objects: list[ObjectData]) -> ObjectData | None:
    color_counts = Counter(int(obj.attrs.get("dominant_color", 0)) for obj in objects)
    candidates = [obj for obj in objects if color_counts[int(obj.attrs.get("dominant_color", 0))] == 1]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _select_unique_relation_defined_object(context: PairContext, objects: list[ObjectData]) -> ObjectData | None:
    repeated_variant = _select_unique_repeated_variant_object(objects)
    if repeated_variant is not None:
        return repeated_variant
    signatures = {obj.id: _relation_signature(context, obj) for obj in objects}
    counts = Counter(signatures.values())
    candidates = [obj for obj in objects if counts[signatures[obj.id]] == 1]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _select_unique_repeated_variant_object(objects: list[ObjectData]) -> ObjectData | None:
    repeat_groups: dict[tuple[tuple[int, int], ...], list[ObjectData]] = defaultdict(list)
    for obj in objects:
        repeat_groups[normalize_pixels(obj.pixels)].append(obj)
    noncanonical_members: list[ObjectData] = []
    for group in repeat_groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda obj: (obj.bbox, obj.id))
        noncanonical_members.extend(ordered[1:])
    if len(noncanonical_members) == 1:
        return noncanonical_members[0]
    return None


def _relation_signature(context: PairContext, obj: ObjectData) -> tuple[tuple[str, int], ...]:
    cached = context.relation_signature_cache.get(obj.id)
    if cached is not None:
        return cached
    counts = Counter()
    for source_id, target_id, relation in context.plan.relations:
        if obj.id not in {source_id, target_id}:
            continue
        category = _relation_category(relation)
        if category is None:
            continue
        counts[category] += 1
    signature = tuple(sorted(counts.items()))
    context.relation_signature_cache[obj.id] = signature
    return signature


def _relation_category(relation: str) -> str | None:
    if relation in {"adjacency", "containment", "repeat"}:
        return relation
    if relation.startswith("aligned_"):
        return "alignment"
    return None


def _components_by_color(grid: Grid) -> list[tuple[int, list[tuple[int, int]]]]:
    rows, cols = grid_shape(grid)
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, list[tuple[int, int]]]] = []
    for row in range(rows):
        for col in range(cols):
            color = grid[row][col]
            if color == 0 or (row, col) in seen:
                continue
            queue: deque[tuple[int, int]] = deque([(row, col)])
            seen.add((row, col))
            cells: list[tuple[int, int]] = []
            while queue:
                current_row, current_col = queue.popleft()
                cells.append((current_row, current_col))
                for delta_row, delta_col in DIRECTIONS_4:
                    next_row = current_row + delta_row
                    next_col = current_col + delta_col
                    next_cell = (next_row, next_col)
                    if not (0 <= next_row < rows and 0 <= next_col < cols):
                        continue
                    if next_cell in seen or grid[next_row][next_col] != color:
                        continue
                    seen.add(next_cell)
                    queue.append(next_cell)
            components.append((color, cells))
    return components


def _crop_region(grid: Grid, bbox: tuple[int, int, int, int]) -> Grid:
    min_row, min_col, max_row, max_col = bbox
    return [row[min_col : max_col + 1] for row in grid[min_row : max_row + 1]]


def _grid_without_component(grid: Grid, component: set[tuple[int, int]]) -> Grid:
    result = [row[:] for row in grid]
    for row, col in component:
        result[row][col] = 0
    return result


def _replace_component(
    grid: Grid,
    source_component: set[tuple[int, int]],
    destination_component: set[tuple[int, int]],
    color: int,
) -> Grid | None:
    rows, cols = grid_shape(grid)
    result = [row[:] for row in grid]
    for row, col in source_component:
        result[row][col] = 0
    for row, col in destination_component:
        if not (0 <= row < rows and 0 <= col < cols):
            return None
        result[row][col] = color
    return result


def _shape_signature(cells: list[tuple[int, int]]) -> frozenset[tuple[int, int]]:
    rows = [row for row, _ in cells]
    cols = [col for _, col in cells]
    min_row = min(rows)
    min_col = min(cols)
    return frozenset((row - min_row, col - min_col) for row, col in cells)


def _is_background(value: int, background_color: int | None) -> bool:
    if background_color is None:
        return value == 0
    return value == background_color


def overlap_1d(left_min: int, left_max: int, right_min: int, right_max: int) -> bool:
    return not (left_max < right_min or right_max < left_min)


def nearest_object_mover(objects: list[ObjectData]) -> ObjectData | None:
    chosen: ObjectData | None = None
    chosen_score: tuple[int, int, int, str] | None = None
    for obj in objects:
        offsets = nearest_object_offsets_candidate(obj, objects)
        if offsets is None:
            continue
        dx, dy = offsets
        score = (abs(dx) + abs(dy), abs(dy), abs(dx), obj.id)
        if chosen_score is None or score < chosen_score:
            chosen = obj
            chosen_score = score
    return chosen


def nearest_object_offsets_candidate(obj: ObjectData, objects: list[ObjectData]) -> tuple[int, int] | None:
    others = [other for other in objects if other.id != obj.id]
    if not others:
        return None
    best: tuple[tuple[int, int, int, str], tuple[int, int]] | None = None
    min_row, min_col, max_row, max_col = obj.bbox
    for other in others:
        other_min_row, other_min_col, other_max_row, other_max_col = other.bbox
        candidates: list[tuple[int, int]] = []
        if overlap_1d(min_row, max_row, other_min_row, other_max_row):
            candidates.append((other_min_col - max_col - 1, 0))
            candidates.append((other_max_col - min_col + 1, 0))
        if overlap_1d(min_col, max_col, other_min_col, other_max_col):
            candidates.append((0, other_min_row - max_row - 1))
            candidates.append((0, other_max_row - min_row + 1))
        if not candidates:
            candidates.extend(
                [
                    (other_min_col - max_col - 1, other_min_row - max_row - 1),
                    (other_min_col - max_col - 1, other_max_row - min_row + 1),
                    (other_max_col - min_col + 1, other_min_row - max_row - 1),
                    (other_max_col - min_col + 1, other_max_row - min_row + 1),
                ]
            )
        for dx, dy in candidates:
            score = (abs(dx) + abs(dy), abs(dy), abs(dx), other.id)
            if best is None or score < best[0]:
                best = (score, (dx, dy))
    return best[1] if best is not None else None


def boundary_direction(obj: ObjectData, objects: list[ObjectData], input_grid: Grid) -> str:
    if len(objects) == 1:
        return single_object_boundary_direction(obj)
    largest = max(objects, key=lambda item: (int(item.attrs.get("area", 0)), tuple(-value for value in item.bbox), item.id))
    height = largest.bbox[2] - largest.bbox[0] + 1
    width = largest.bbox[3] - largest.bbox[1] + 1
    if height > width:
        top_distance = sum(item.bbox[0] for item in objects)
        bottom_distance = sum(len(input_grid) - 1 - item.bbox[2] for item in objects)
        return "up" if top_distance <= bottom_distance else "down"
    if width > height:
        left_distance = sum(item.bbox[1] for item in objects)
        right_distance = sum(len(input_grid[0]) - 1 - item.bbox[3] for item in objects)
        return "left" if left_distance <= right_distance else "right"
    return single_object_boundary_direction(largest)


def single_object_boundary_direction(obj: ObjectData) -> str:
    canvas_height = int(obj.attrs.get("canvas_height", 0))
    canvas_width = int(obj.attrs.get("canvas_width", 0))
    min_row, min_col, max_row, max_col = obj.bbox
    distances = {
        "up": min_row,
        "down": canvas_height - 1 - max_row,
        "left": min_col,
        "right": canvas_width - 1 - max_col,
    }
    return min(distances, key=lambda direction: (distances[direction], direction))
