from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from statistics import mean
from typing import Any

from common import (
    Grid,
    clone_object,
    exact_match,
    grid_shape,
    object_crop_grid,
    pixel_accuracy,
    render_object_list,
    replace_object_pixels,
)
from configs import AppendixBConfig
from methods import (
    MethodHypothesis,
    PairContext,
    boundary_offsets,
    build_h_norm,
    build_pair_context,
    classify_pair,
    infer_single_object_translation,
    nearest_object_offsets,
    recolor_source_role,
    resolve_role_color,
    select_object,
)


SMALL_INTEGER_OFFSETS = (-3, -2, -1, 0, 1, 2, 3)
X_PARAMS: tuple[int | str, ...] = (
    *SMALL_INTEGER_OFFSETS,
    "input_width",
    "-input_width",
    "object_width",
    "-object_width",
    "to_input_center_dx",
    "to_largest_object_center_dx",
    "to_boundary_dx",
    "to_nearest_object_dx",
)
Y_PARAMS: tuple[int | str, ...] = (
    *SMALL_INTEGER_OFFSETS,
    "input_height",
    "-input_height",
    "object_height",
    "-object_height",
    "to_input_center_dy",
    "to_largest_object_center_dy",
    "to_boundary_dy",
    "to_nearest_object_dy",
)

DEFAULT_TRAIN_OBJECTIVE_PROXY: dict[str, Any] = {
    "residual": {
        "exact_miss_weight": 2.0,
        "pixel_miss_weight": 1.0,
    },
    "lambda_program": 0.05,
    "lambda_hypothesis": 0.05,
    "program_complexity": {
        "selector_base": 0.5,
        "template_weights": {
            "identity": 1.0,
            "delete": 1.0,
            "crop_selected_bbox": 1.0,
            "recolor": 1.5,
            "translate": 1.5,
        },
        "render_weights": {
            "render_all": 0.5,
            "render_selected": 0.75,
            "crop_selected_bbox": 1.0,
        },
        "literal_param_cost": 0.25,
        "symbolic_param_cost": 0.5,
    },
    "hypothesis_complexity": {
        "background_mode_weights": {
            "top1": 0.0,
            "top2": 0.25,
            "no_fixed_background": 0.5,
        },
        "radius_step_cost": 0.25,
        "theta_threshold_cost": 0.5,
        "feature_subset_costs": {
            "features:full8": 0.5,
            "features:raw_full8": 0.5,
        },
        "preorder_profile_costs": {
            "preorders:config_default": 0.75,
        },
        "weight_id_costs": {
            "W_u": 0.25,
            "W_m": 0.25,
            "W_r": 0.25,
            "W_g": 0.25,
        },
    },
}


@dataclass(frozen=True)
class CandidateKey:
    selector: str
    template: str
    render: str
    params: tuple[tuple[str, int | str], ...]


@dataclass(frozen=True)
class CandidateExplanation:
    hypothesis: MethodHypothesis
    selector: str
    template: str
    render: str
    params: tuple[tuple[str, int | str], ...]
    theta_norm: tuple[Any, ...]
    h_norm: tuple[Any, ...]
    sigma: tuple[Any, ...]
    train_exact_rate: float
    train_accuracy: float
    train_residual_loss: float
    train_program_complexity: float
    train_hypothesis_complexity: float
    train_j_score: float

    @property
    def debug_name(self) -> str:
        if not self.params:
            return f"{self.hypothesis.plan_id}|{self.selector}|{self.template}|{self.render}"
        params = ",".join(f"{key}={value}" for key, value in self.params)
        return f"{self.hypothesis.plan_id}|{self.selector}|{self.template}|{self.render}|{params}"


def search_method_candidates(
    train_pairs: list[dict[str, Grid]],
    hypotheses: list[MethodHypothesis],
    config: AppendixBConfig,
) -> tuple[list[CandidateExplanation], int]:
    all_candidates: list[CandidateExplanation] = []
    objective_proxy = resolve_train_objective_proxy(config)
    for hypothesis in hypotheses:
        contexts = [
            build_pair_context(index, pair["input"], pair["output"], hypothesis, config)
            for index, pair in enumerate(train_pairs)
        ]
        if not contexts:
            continue
        pair_candidate_sets = [enumerate_exact_pair_candidates(context, config) for context in contexts]
        union_keys: set[CandidateKey] = set().union(*pair_candidate_sets)
        if not union_keys:
            continue
        h_norm = build_h_norm(contexts, hypothesis, config)
        hypothesis_complexity = _hypothesis_complexity(hypothesis, objective_proxy)
        for key in sorted(union_keys, key=_candidate_key_sort_key):
            exact_scores: list[float] = []
            accuracies: list[float] = []
            for context in contexts:
                _, exact_flag, accuracy = evaluate_candidate_key(context, key)
                exact_scores.append(1.0 if exact_flag else 0.0)
                accuracies.append(accuracy)
            train_exact_rate = mean(exact_scores)
            train_accuracy = mean(accuracies)
            train_residual_loss = _residual_loss(train_exact_rate, train_accuracy, objective_proxy)
            train_program_complexity = _program_complexity(key, objective_proxy)
            train_j_score = _train_j_score(
                train_residual_loss,
                train_program_complexity,
                hypothesis_complexity,
                objective_proxy,
            )
            candidate = CandidateExplanation(
                hypothesis=hypothesis,
                selector=key.selector,
                template=key.template,
                render=key.render,
                params=key.params,
                theta_norm=normalize_theta(key, contexts[0]),
                h_norm=h_norm,
                sigma=(key.template, key.selector, key.render, normalize_theta(key, contexts[0]), h_norm),
                train_exact_rate=train_exact_rate,
                train_accuracy=train_accuracy,
                train_residual_loss=train_residual_loss,
                train_program_complexity=train_program_complexity,
                train_hypothesis_complexity=hypothesis_complexity,
                train_j_score=train_j_score,
            )
            if candidate.train_accuracy > 0.0:
                all_candidates.append(candidate)
    deduped = _dedupe_by_sigma(all_candidates)
    ranked = sorted(deduped, key=lambda candidate: _candidate_rank_key(candidate, config))
    budget = int(config.search_bounds["candidate_program_cap_per_fold"])
    return ranked[:budget], len(all_candidates)


def resolve_train_objective_proxy(config: AppendixBConfig) -> dict[str, Any]:
    proxy = deepcopy(DEFAULT_TRAIN_OBJECTIVE_PROXY)
    _deep_update(proxy, config.evaluation.get("train_objective_proxy", {}))
    return proxy


def build_failed_train_objective(config: AppendixBConfig) -> dict[str, float]:
    objective_proxy = resolve_train_objective_proxy(config)
    train_residual_loss = _residual_loss(0.0, 0.0, objective_proxy)
    train_program_complexity = 0.0
    train_hypothesis_complexity = 0.0
    train_j_score = _train_j_score(
        train_residual_loss,
        train_program_complexity,
        train_hypothesis_complexity,
        objective_proxy,
    )
    return {
        "train_residual_loss": train_residual_loss,
        "train_program_complexity": train_program_complexity,
        "train_hypothesis_complexity": train_hypothesis_complexity,
        "train_j_score": train_j_score,
    }


def enumerate_exact_pair_candidates(context: PairContext, config: AppendixBConfig) -> set[CandidateKey]:
    candidates: set[CandidateKey] = set()
    allowed_roles = config.signature["theta_norm"]["recolor"]["allowed_roles"]
    input_shape = grid_shape(context.input_grid)
    output_shape = grid_shape(context.output_grid)
    same_size = input_shape == output_shape
    pair_label = classify_pair(context.input_grid, context.output_grid)

    allow_identity = pair_label in {None, "identity"}
    allow_delete = pair_label in {None, "single_object_delete"}
    allow_recolor = pair_label in {None, "single_object_recolor"}
    allow_translate = pair_label in {None, "single_object_translate"}
    allow_crop = pair_label in {None, "crop_selected_bbox"}
    observed_translation = infer_single_object_translation(context.input_grid, context.output_grid) if pair_label == "single_object_translate" else None

    for selector in config.whitelists["selectors"]:
        selected = select_object(context, selector)
        if selected is None:
            continue

        if same_size and allow_identity:
            key = CandidateKey(selector=selector, template="identity", render="render_all", params=())
            _, exact_flag, _ = evaluate_candidate_key(context, key)
            if exact_flag:
                candidates.add(key)

            key = CandidateKey(selector=selector, template="identity", render="render_selected", params=())
            _, exact_flag, _ = evaluate_candidate_key(context, key)
            if exact_flag:
                candidates.add(key)

        if same_size and allow_delete:
            key = CandidateKey(selector=selector, template="delete", render="render_all", params=())
            _, exact_flag, _ = evaluate_candidate_key(context, key)
            if exact_flag:
                candidates.add(key)

        if same_size and allow_recolor:
            source_role = recolor_source_role(selected, context)
            for target_role in allowed_roles:
                params = (("source_role", source_role), ("target_role", str(target_role)))
                for render in ("render_all", "render_selected"):
                    key = CandidateKey(selector=selector, template="recolor", render=render, params=params)
                    _, exact_flag, _ = evaluate_candidate_key(context, key)
                    if exact_flag:
                        candidates.add(key)

        if same_size and allow_translate:
            for dx_param, dy_param in _translate_param_candidates(selected, context, observed_translation):
                if dx_param == 0 and dy_param == 0:
                    continue
                params = (("dx", dx_param), ("dy", dy_param))
                for render in ("render_all", "render_selected"):
                    key = CandidateKey(selector=selector, template="translate", render=render, params=params)
                    _, exact_flag, _ = evaluate_candidate_key(context, key)
                    if exact_flag:
                        candidates.add(key)

        if allow_crop and output_shape != input_shape:
            key = CandidateKey(selector=selector, template="crop_selected_bbox", render="crop_selected_bbox", params=())
            _, exact_flag, _ = evaluate_candidate_key(context, key)
            if exact_flag:
                candidates.add(key)
    return candidates


def evaluate_candidate(
    candidate: CandidateExplanation,
    input_grid: Grid,
    output_grid: Grid,
    pair_index: int,
    config: AppendixBConfig,
) -> tuple[Grid, bool, float]:
    context = build_pair_context(pair_index, input_grid, output_grid, candidate.hypothesis, config)
    key = CandidateKey(
        selector=candidate.selector,
        template=candidate.template,
        render=candidate.render,
        params=candidate.params,
    )
    return evaluate_candidate_key(context, key)


def evaluate_candidate_key(context: PairContext, candidate_key: CandidateKey) -> tuple[Grid, bool, float]:
    selected = select_object(context, candidate_key.selector)
    background_color = context.bg_color
    if selected is None:
        blank = [[background_color for _ in range(grid_shape(context.input_grid)[1])] for _ in range(grid_shape(context.input_grid)[0])]
        if candidate_key.render == "crop_selected_bbox":
            blank = [[background_color]]
        return blank, False, pixel_accuracy(blank, context.output_grid)

    transformed_objects = [clone_object(obj) for obj in context.plan.objects]
    selected_after: ObjectData | None = None
    new_objects: list[Any] = []
    for obj in transformed_objects:
        if obj.id != selected.id:
            new_objects.append(obj)
            continue
        transformed = _apply_template(candidate_key, obj, context)
        if transformed is None:
            selected_after = None
            continue
        selected_after = transformed
        new_objects.append(transformed)

    predicted = _render_candidate(candidate_key, new_objects, selected_after, context)
    return predicted, exact_match(predicted, context.output_grid), pixel_accuracy(predicted, context.output_grid)


def normalize_theta(candidate_key: CandidateKey, context: PairContext) -> tuple[Any, ...]:
    if candidate_key.template in {"identity", "delete", "crop_selected_bbox"}:
        return ()
    if candidate_key.template == "translate":
        params = dict(candidate_key.params)
        return (params["dx"], params["dy"])
    if candidate_key.template == "recolor":
        params = dict(candidate_key.params)
        return (params["source_role"], params["target_role"])
    raise ValueError(f"Unsupported template for theta normalization: {candidate_key.template}")


def _apply_template(candidate_key: CandidateKey, obj: Any, context: PairContext) -> Any:
    params = dict(candidate_key.params)
    if candidate_key.template == "identity":
        return clone_object(obj)
    if candidate_key.template == "delete":
        return None
    if candidate_key.template == "crop_selected_bbox":
        return clone_object(obj)
    if candidate_key.template == "recolor":
        target_role = str(params["target_role"])
        target_color = resolve_role_color(target_role, context)
        if target_color is None:
            return clone_object(obj)
        pixel_colors = {cell: int(target_color) for cell in obj.pixel_colors}
        recolored = replace_object_pixels(obj, set(obj.pixels), pixel_colors)
        recolored.attrs["dominant_color"] = int(target_color)
        recolored.attrs["color"] = int(target_color)
        return recolored
    if candidate_key.template == "translate":
        dx = _resolve_numeric_param(params["dx"], obj, context)
        dy = _resolve_numeric_param(params["dy"], obj, context)
        pixels = {(row + dy, col + dx) for row, col in obj.pixels}
        pixel_colors = {(row + dy, col + dx): color for (row, col), color in obj.pixel_colors.items()}
        return replace_object_pixels(obj, pixels, pixel_colors)
    raise ValueError(f"Unsupported template: {candidate_key.template}")


def _render_candidate(candidate_key: CandidateKey, objects: list[Any], selected: Any, context: PairContext) -> Grid:
    input_shape = grid_shape(context.input_grid)
    if candidate_key.render == "render_all":
        return render_object_list(objects, context.bg_color, input_shape)
    if candidate_key.render == "render_selected":
        selected_objects = [selected] if selected is not None else []
        return render_object_list(selected_objects, context.bg_color, input_shape)
    if candidate_key.render == "crop_selected_bbox":
        if selected is None:
            return [[context.bg_color]]
        return object_crop_grid(selected, context.bg_color)
    raise ValueError(f"Unsupported render mode: {candidate_key.render}")


def _resolve_numeric_param(value: int | str, obj: Any, context: PairContext) -> int:
    if isinstance(value, int):
        return value
    sign = -1 if value.startswith("-") else 1
    token = value[1:] if sign == -1 else value
    resolved = _resolve_symbolic_param(token, obj, context)
    return sign * resolved


def _resolve_symbolic_param(token: str, obj: Any, context: PairContext) -> int:
    input_rows, input_cols = grid_shape(context.input_grid)
    if token == "input_width":
        return input_cols
    if token == "input_height":
        return input_rows
    if token == "object_width":
        return int(obj.attrs.get("width", 0))
    if token == "object_height":
        return int(obj.attrs.get("height", 0))
    if token == "to_input_center_dx":
        return int(round(((input_cols - 1) / 2) - float(obj.attrs.get("center_col", 0.0))))
    if token == "to_input_center_dy":
        return int(round(((input_rows - 1) / 2) - float(obj.attrs.get("center_row", 0.0))))
    if token == "to_largest_object_center_dx":
        largest = max(context.plan.objects, key=lambda item: (int(item.attrs.get("area", 0)), tuple(-value for value in item.bbox), item.id), default=None)
        if largest is None:
            return 0
        return int(round(float(largest.attrs.get("center_col", 0.0)) - float(obj.attrs.get("center_col", 0.0))))
    if token == "to_largest_object_center_dy":
        largest = max(context.plan.objects, key=lambda item: (int(item.attrs.get("area", 0)), tuple(-value for value in item.bbox), item.id), default=None)
        if largest is None:
            return 0
        return int(round(float(largest.attrs.get("center_row", 0.0)) - float(obj.attrs.get("center_row", 0.0))))
    if token == "to_boundary_dx":
        dx, _ = boundary_offsets(obj, context.plan.objects, context.input_grid)
        return dx
    if token == "to_boundary_dy":
        _, dy = boundary_offsets(obj, context.plan.objects, context.input_grid)
        return dy
    if token == "to_nearest_object_dx":
        offsets = nearest_object_offsets(obj, context.plan.objects)
        return offsets[0] if offsets is not None else 0
    if token == "to_nearest_object_dy":
        offsets = nearest_object_offsets(obj, context.plan.objects)
        return offsets[1] if offsets is not None else 0
    raise ValueError(f"Unsupported symbolic parameter: {token}")


def _translate_param_candidates(
    obj: Any,
    context: PairContext,
    observed_translation: tuple[int, int] | None,
) -> list[tuple[int | str, int | str]]:
    if observed_translation is None:
        return list(product(X_PARAMS, Y_PARAMS))
    observed_dx, observed_dy = observed_translation
    x_candidates = [param for param in X_PARAMS if _resolve_numeric_param(param, obj, context) == observed_dx]
    y_candidates = [param for param in Y_PARAMS if _resolve_numeric_param(param, obj, context) == observed_dy]
    if not x_candidates:
        x_candidates = [observed_dx]
    if not y_candidates:
        y_candidates = [observed_dy]
    return list(product(tuple(dict.fromkeys(x_candidates)), tuple(dict.fromkeys(y_candidates))))


def _dedupe_by_sigma(candidates: list[CandidateExplanation]) -> list[CandidateExplanation]:
    best_by_sigma: dict[tuple[Any, ...], CandidateExplanation] = {}
    for candidate in candidates:
        existing = best_by_sigma.get(candidate.sigma)
        if existing is None or (candidate.train_j_score, -candidate.train_exact_rate, -candidate.train_accuracy, candidate.debug_name) < (
            existing.train_j_score,
            -existing.train_exact_rate,
            -existing.train_accuracy,
            existing.debug_name,
        ):
            best_by_sigma[candidate.sigma] = candidate
    return list(best_by_sigma.values())


def _candidate_key_sort_key(candidate_key: CandidateKey) -> tuple[Any, ...]:
    normalized_params = tuple((key, str(value)) for key, value in candidate_key.params)
    return (candidate_key.selector, candidate_key.template, candidate_key.render, normalized_params)


def _candidate_rank_key(candidate: CandidateExplanation, config: AppendixBConfig) -> tuple[Any, ...]:
    selectors = list(config.whitelists["selectors"])
    templates = list(config.whitelists["templates"])
    renders = list(config.whitelists["renders"])
    return (
        candidate.train_j_score,
        -candidate.train_exact_rate,
        -candidate.train_accuracy,
        templates.index(candidate.template) if candidate.template in templates else 999,
        selectors.index(candidate.selector) if candidate.selector in selectors else 999,
        renders.index(candidate.render) if candidate.render in renders else 999,
        _recolor_param_rank(candidate),
        candidate.hypothesis.plan_id,
        candidate.debug_name,
    )


def _recolor_param_rank(candidate: CandidateExplanation) -> tuple[Any, ...]:
    if candidate.template != "recolor":
        return (999, 999)
    params = dict(candidate.params)
    target_role = str(params.get("target_role", ""))
    source_role = str(params.get("source_role", ""))
    target_order = (
        "largest_object_color",
        "dominant_non_background",
        "second_non_background",
        "unique_non_background",
        "background",
    )
    source_order = (
        "other_non_background",
        "second_non_background",
        "dominant_non_background",
        "unique_non_background",
        "background",
    )
    target_rank = target_order.index(target_role) if target_role in target_order else len(target_order)
    source_rank = source_order.index(source_role) if source_role in source_order else len(source_order)
    return (target_rank, source_rank)


def _deep_update(target: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
            continue
        target[key] = value


def _residual_loss(train_exact_rate: float, train_accuracy: float, objective_proxy: dict[str, Any]) -> float:
    residual_config = objective_proxy["residual"]
    exact_miss_weight = float(residual_config["exact_miss_weight"])
    pixel_miss_weight = float(residual_config["pixel_miss_weight"])
    return exact_miss_weight * (1.0 - train_exact_rate) + pixel_miss_weight * (1.0 - train_accuracy)


def _program_complexity(candidate_key: CandidateKey, objective_proxy: dict[str, Any]) -> float:
    program_config = objective_proxy["program_complexity"]
    template_weights = program_config["template_weights"]
    render_weights = program_config["render_weights"]
    literal_param_cost = float(program_config["literal_param_cost"])
    symbolic_param_cost = float(program_config["symbolic_param_cost"])

    complexity = float(program_config["selector_base"])
    complexity += float(template_weights.get(candidate_key.template, 1.0))
    complexity += float(render_weights.get(candidate_key.render, 0.5))
    for _, value in candidate_key.params:
        complexity += literal_param_cost if isinstance(value, int) else symbolic_param_cost
    return complexity


def _hypothesis_complexity(hypothesis: MethodHypothesis, objective_proxy: dict[str, Any]) -> float:
    hypothesis_config = objective_proxy["hypothesis_complexity"]
    background_mode_weights = hypothesis_config["background_mode_weights"]
    feature_subset_costs = hypothesis_config["feature_subset_costs"]
    preorder_profile_costs = hypothesis_config["preorder_profile_costs"]
    weight_id_costs = hypothesis_config["weight_id_costs"]
    theta_threshold_cost = float(hypothesis_config["theta_threshold_cost"])
    radius_step_cost = float(hypothesis_config["radius_step_cost"])

    complexity = float(background_mode_weights.get(hypothesis.bg_mode, 0.0))
    complexity += max(hypothesis.r - 1, 0) * radius_step_cost
    complexity += float(feature_subset_costs.get(hypothesis.feature_subset_id, 0.0))
    complexity += float(preorder_profile_costs.get(hypothesis.preorder_profile_id, 0.0))
    complexity += float(weight_id_costs.get(hypothesis.weight_id, 0.0))
    if hypothesis.theta is not None and hypothesis.theta < 1.0:
        complexity += theta_threshold_cost
    return complexity


def _train_j_score(
    train_residual_loss: float,
    train_program_complexity: float,
    train_hypothesis_complexity: float,
    objective_proxy: dict[str, Any],
) -> float:
    return (
        train_residual_loss
        + float(objective_proxy["lambda_program"]) * train_program_complexity
        + float(objective_proxy["lambda_hypothesis"]) * train_hypothesis_complexity
    )
