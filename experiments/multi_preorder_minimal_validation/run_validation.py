from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean
from typing import Any

from common import REPO_ROOT, grid_shape, resolve_background_color, shift_grid, write_json
from configs import AppendixAConfig, AppendixBConfig, PrimaryTaskEntry, load_appendix_a, load_appendix_b, load_arc_task
from methods import build_method_hypotheses, classify_pair, task_gate_summary
from templates import CandidateExplanation, build_failed_train_objective, evaluate_candidate, resolve_train_objective_proxy, search_method_candidates


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_APPENDIX_A = SCRIPT_DIR / "appendix_a_tasks.v0_9.json"
DEFAULT_APPENDIX_B = SCRIPT_DIR / "appendix_b_config.v0_9.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "validation_report.v0_9.json"


def main() -> None:
    args = parse_args()
    appendix_a = load_appendix_a(args.appendix_a)
    appendix_b = load_appendix_b(args.appendix_b)
    requested_methods = _parse_csv(args.methods) or list(appendix_b.comparison_methods)
    requested_tasks = _parse_csv(args.tasks)

    task_entries = [entry for entry in appendix_a.primary_tasks if not requested_tasks or entry.task_id in requested_tasks]
    if args.limit is not None:
        task_entries = task_entries[: args.limit]

    method_hypotheses = {method: build_method_hypotheses(appendix_b, method) for method in requested_methods}
    report = {
        "experiment_id": appendix_b.experiment_id,
        "appendix_a": str(args.appendix_a.relative_to(REPO_ROOT)),
        "appendix_b": str(args.appendix_b.relative_to(REPO_ROOT)),
        "train_objective_proxy": resolve_train_objective_proxy(appendix_b),
        "methods": requested_methods,
        "tasks": [],
    }

    for entry in task_entries:
        task_report = evaluate_task(
            entry,
            appendix_a,
            appendix_b,
            requested_methods,
            method_hypotheses,
            args.skip_perturbations,
            args.max_folds,
        )
        report["tasks"].append(task_report)
        print(_task_console_line(task_report, requested_methods))

    report["summary"] = build_summary(report["tasks"], requested_methods, appendix_b)
    report["formal_verdict"] = build_formal_verdict(report["summary"], report["tasks"], requested_methods, appendix_b)
    write_json(args.output, report)
    if report["formal_verdict"] is not None:
        print(
            "Formal verdict: "
            f"{report['formal_verdict']['status']} "
            f"(pass={report['formal_verdict']['passes_formal_threshold']})"
        )
    print(f"Wrote report to {args.output}")


def evaluate_task(
    entry: PrimaryTaskEntry,
    appendix_a: AppendixAConfig,
    appendix_b: AppendixBConfig,
    methods: list[str],
    method_hypotheses: dict[str, list[Any]],
    skip_perturbations: bool,
    max_folds: int | None,
) -> dict[str, Any]:
    task_path = REPO_ROOT / appendix_a.dataset_dir / f"{entry.task_id}.json"
    task = load_arc_task(task_path)
    gate = task_gate_summary(task, entry)
    folds: list[dict[str, Any]] = []
    fold_count = len(task["train"]) if max_folds is None else min(len(task["train"]), max_folds)
    for holdout_index in range(fold_count):
        train_pairs = [pair for index, pair in enumerate(task["train"]) if index != holdout_index]
        holdout_pair = task["train"][holdout_index]
        fold_report = {"holdout_index": holdout_index, "methods": {}}
        for method in methods:
            top_candidates, candidate_count = search_method_candidates(train_pairs, method_hypotheses[method], appendix_b)
            top1 = top_candidates[0] if top_candidates else None
            if top1 is None:
                predicted = _blank_prediction(holdout_pair["input"], holdout_pair["output"])
                exact_flag = False
                accuracy = 0.0
                top1_sigma = None
                top1_name = None
                top1_train_objective = build_failed_train_objective(appendix_b)
            else:
                predicted, exact_flag, accuracy = evaluate_candidate(top1, holdout_pair["input"], holdout_pair["output"], holdout_index, appendix_b)
                top1_sigma = top1.sigma
                top1_name = top1.debug_name
                top1_train_objective = {
                    "train_residual_loss": top1.train_residual_loss,
                    "train_program_complexity": top1.train_program_complexity,
                    "train_hypothesis_complexity": top1.train_hypothesis_complexity,
                    "train_j_score": top1.train_j_score,
                }

            perturbation_report = []
            if not skip_perturbations and top_candidates:
                perturbation_report = evaluate_perturbations(task, holdout_index, method_hypotheses[method], top_candidates, appendix_b)

            fold_report["methods"][method] = {
                "candidate_count": candidate_count,
                "top_k": [_serialize_candidate(candidate) for candidate in top_candidates],
                "top1_exact": exact_flag,
                "top1_accuracy": accuracy,
                "top1_sigma": top1_sigma,
                "top1_name": top1_name,
                "top1_train_j_score": float(top1_train_objective["train_j_score"]),
                "top1_train_objective": top1_train_objective,
                "prediction_shape": grid_shape(predicted),
                "train_score_compression_advantage": compute_train_score_compression(top_candidates),
                "perturbations": perturbation_report,
            }
        folds.append(fold_report)

    aggregate = aggregate_task_methods(folds, methods, appendix_b)
    return {
        "task_id": entry.task_id,
        "observed_label": entry.observed_label,
        "template_family": entry.template_family,
        "gate": gate,
        "folds": folds,
        "aggregate": aggregate,
    }


def evaluate_perturbations(
    task: dict[str, Any],
    holdout_index: int,
    hypotheses: list[Any],
    original_top_candidates: list[CandidateExplanation],
    appendix_b: AppendixBConfig,
) -> list[dict[str, Any]]:
    original_sigma_set = {tuple(candidate.sigma) for candidate in original_top_candidates}
    original_top1_sigma = tuple(original_top_candidates[0].sigma)
    results: list[dict[str, Any]] = []
    for perturbation in appendix_b.perturbations:
        perturbed_task = apply_perturbation(task, perturbation)
        perturbed_train = [pair for index, pair in enumerate(perturbed_task["train"]) if index != holdout_index]
        perturbed_candidates, _ = search_method_candidates(perturbed_train, hypotheses, appendix_b)
        perturbed_sigma_set = {tuple(candidate.sigma) for candidate in perturbed_candidates}
        union = original_sigma_set | perturbed_sigma_set
        overlap = original_sigma_set & perturbed_sigma_set
        eq_k = len(overlap) / len(union) if union else 1.0
        top1_match = bool(perturbed_candidates) and tuple(perturbed_candidates[0].sigma) == original_top1_sigma
        results.append(
            {
                "perturbation_id": perturbation["id"],
                "top1_signature_match": top1_match,
                "eq_k": eq_k,
                "passes_tau": eq_k >= float(appendix_b.protocol["tau_eq"]),
            }
        )
    return results


def apply_perturbation(task: dict[str, Any], perturbation: dict[str, Any]) -> dict[str, Any]:
    if perturbation["id"] == "P_color":
        return _apply_color_permutation(task)
    if perturbation["id"] == "P_shift":
        return _apply_shift(task)
    raise ValueError(f"Unsupported perturbation id: {perturbation['id']}")


def aggregate_task_methods(folds: list[dict[str, Any]], methods: list[str], appendix_b: AppendixBConfig) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for method in methods:
        method_folds = [fold["methods"][method] for fold in folds]
        exact_flags = [1.0 if item["top1_exact"] else 0.0 for item in method_folds]
        accuracies = [float(item["top1_accuracy"]) for item in method_folds]
        compression = [float(item["train_score_compression_advantage"]) for item in method_folds]
        train_j_scores = [float(item["top1_train_j_score"]) for item in method_folds]
        residual_losses = [float(item["top1_train_objective"]["train_residual_loss"]) for item in method_folds]
        program_complexities = [float(item["top1_train_objective"]["train_program_complexity"]) for item in method_folds]
        hypothesis_complexities = [float(item["top1_train_objective"]["train_hypothesis_complexity"]) for item in method_folds]
        perturbation_flags = [
            1.0
            for item in method_folds
            for perturbation in item["perturbations"]
            if perturbation["top1_signature_match"] and perturbation["passes_tau"]
        ]
        perturbation_total = sum(len(item["perturbations"]) for item in method_folds)
        aggregate[method] = {
            "task_exact_match": all(item["top1_exact"] for item in method_folds),
            "mean_fold_exact": mean(exact_flags) if exact_flags else 0.0,
            "mean_pixel_accuracy": mean(accuracies) if accuracies else 0.0,
            "mean_top1_train_j_score": mean(train_j_scores) if train_j_scores else 0.0,
            "mean_train_residual_loss": mean(residual_losses) if residual_losses else 0.0,
            "mean_train_program_complexity": mean(program_complexities) if program_complexities else 0.0,
            "mean_train_hypothesis_complexity": mean(hypothesis_complexities) if hypothesis_complexities else 0.0,
            "train_score_compression_advantage": mean(compression) if compression else 0.0,
            "robust_equivalence_rate": (sum(perturbation_flags) / perturbation_total) if perturbation_total else None,
        }
    if "multi_preorder" in aggregate:
        aggregate["multi_preorder_vs_baselines"] = compare_against_baselines(aggregate, appendix_b)
    return aggregate


def compare_against_baselines(method_aggregate: dict[str, Any], appendix_b: AppendixBConfig) -> dict[str, Any]:
    target = method_aggregate["multi_preorder"]
    baselines = [name for name in method_aggregate if name not in {"multi_preorder", "multi_preorder_vs_baselines"}]
    exact_scores = {}
    accuracy_gains = {}
    train_j_score_gains = {}
    for baseline_name in baselines:
        baseline = method_aggregate[baseline_name]
        if target["mean_fold_exact"] > baseline["mean_fold_exact"]:
            exact_scores[baseline_name] = 1.0
        elif target["mean_fold_exact"] < baseline["mean_fold_exact"]:
            exact_scores[baseline_name] = 0.0
        else:
            exact_scores[baseline_name] = float(appendix_b.evaluation["paired_baseline_metrics"]["tie_score"])
        accuracy_gains[baseline_name] = target["mean_pixel_accuracy"] - baseline["mean_pixel_accuracy"]
        train_j_score_gains[baseline_name] = baseline["mean_top1_train_j_score"] - target["mean_top1_train_j_score"]
    return {
        "paired_exact_match_win_rate": exact_scores,
        "paired_mean_pixel_accuracy_gain": accuracy_gains,
        "paired_mean_train_j_score_gain": train_j_score_gains,
    }


def build_summary(task_reports: list[dict[str, Any]], methods: list[str], appendix_b: AppendixBConfig) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for method in methods:
        aggregates = [task["aggregate"][method] for task in task_reports]
        summary[method] = {
            "top1_exact_match_tasks": sum(1 for item in aggregates if item["task_exact_match"]),
            "mean_pixel_accuracy": mean(item["mean_pixel_accuracy"] for item in aggregates) if aggregates else 0.0,
            "mean_top1_train_j_score": mean(item["mean_top1_train_j_score"] for item in aggregates) if aggregates else 0.0,
            "mean_train_residual_loss": mean(item["mean_train_residual_loss"] for item in aggregates) if aggregates else 0.0,
            "mean_train_program_complexity": mean(item["mean_train_program_complexity"] for item in aggregates) if aggregates else 0.0,
            "mean_train_hypothesis_complexity": mean(item["mean_train_hypothesis_complexity"] for item in aggregates) if aggregates else 0.0,
            "train_score_compression_advantage": mean(item["train_score_compression_advantage"] for item in aggregates) if aggregates else 0.0,
            "robust_equivalence_rate": mean(item["robust_equivalence_rate"] for item in aggregates if item["robust_equivalence_rate"] is not None) if any(item["robust_equivalence_rate"] is not None for item in aggregates) else None,
        }
    if "multi_preorder" in methods:
        baseline_names = [method for method in methods if method != "multi_preorder"]
        win_rates, acc_gains = compute_fold_level_pairwise_metrics(task_reports, baseline_names, appendix_b)
        summary["multi_preorder_vs_baselines"] = {
            "paired_exact_match_win_rate": win_rates,
            "paired_mean_pixel_accuracy_gain": acc_gains,
            "passes_fraction_threshold": sum(1 for value in win_rates.values() if value >= float(appendix_b.evaluation["paired_baseline_metrics"]["win_rate_min_baseline_fraction_with_ge_0_5"])) >= ((len(win_rates) + 1) // 2),
        }
    return summary


def compute_train_score_compression(candidates: list[CandidateExplanation]) -> float:
    if not candidates:
        return 0.0
    if len(candidates) == 1:
        return 0.0
    tail_mean = mean(candidate.train_j_score for candidate in candidates[1:])
    return tail_mean - candidates[0].train_j_score


def compute_fold_level_pairwise_metrics(
    task_reports: list[dict[str, Any]],
    baseline_names: list[str],
    appendix_b: AppendixBConfig,
) -> tuple[dict[str, float], dict[str, float]]:
    tie_score = float(appendix_b.evaluation["paired_baseline_metrics"]["tie_score"])
    win_rates: dict[str, float] = {}
    acc_gains: dict[str, float] = {}
    for baseline in baseline_names:
        exact_scores: list[float] = []
        accuracy_gains: list[float] = []
        for task in task_reports:
            for fold in task["folds"]:
                mp = fold["methods"]["multi_preorder"]
                base = fold["methods"][baseline]
                mp_exact = 1 if mp["top1_exact"] else 0
                base_exact = 1 if base["top1_exact"] else 0
                if mp_exact > base_exact:
                    exact_scores.append(1.0)
                elif mp_exact < base_exact:
                    exact_scores.append(0.0)
                else:
                    exact_scores.append(tie_score)
                accuracy_gains.append(float(mp["top1_accuracy"]) - float(base["top1_accuracy"]))
        win_rates[baseline] = mean(exact_scores) if exact_scores else 0.0
        acc_gains[baseline] = mean(accuracy_gains) if accuracy_gains else 0.0
    return win_rates, acc_gains


def build_formal_verdict(
    summary: dict[str, Any],
    task_reports: list[dict[str, Any]],
    methods: list[str],
    appendix_b: AppendixBConfig,
) -> dict[str, Any] | None:
    if "multi_preorder" not in methods:
        return None

    baseline_names = [method for method in methods if method != "multi_preorder"]
    if not baseline_names:
        return None

    win_rates, acc_gains = compute_fold_level_pairwise_metrics(task_reports, baseline_names, appendix_b)
    exact_threshold = float(appendix_b.evaluation["paired_baseline_metrics"]["win_rate_min_baseline_fraction_with_ge_0_5"])
    required_baselines = (len(baseline_names) + 1) // 2
    criterion_1_pass = sum(1 for value in win_rates.values() if value >= exact_threshold) >= required_baselines

    mean_accuracy_gain = mean(acc_gains.values()) if acc_gains else 0.0
    criterion_2_pass = mean_accuracy_gain > 0.0

    multi_preorder_summary = summary["multi_preorder"]
    baseline_mean_top1_train_j_score = mean(summary[baseline]["mean_top1_train_j_score"] for baseline in baseline_names)
    baseline_mean_robustness = mean(
        summary[baseline]["robust_equivalence_rate"]
        for baseline in baseline_names
        if summary[baseline]["robust_equivalence_rate"] is not None
    )

    shared_compression_relation = compare_secondary_endpoint(
        multi_preorder_summary["mean_top1_train_j_score"],
        baseline_mean_top1_train_j_score,
        lower_is_better=True,
    )
    robustness_relation = compare_secondary_endpoint(
        multi_preorder_summary["robust_equivalence_rate"],
        baseline_mean_robustness,
        lower_is_better=False,
    )
    criterion_3_pass = (
        (shared_compression_relation == "strictly_better" and robustness_relation in {"strictly_better", "not_worse"})
        or (robustness_relation == "strictly_better" and shared_compression_relation in {"strictly_better", "not_worse"})
    )

    passes_formal_threshold = criterion_1_pass and criterion_2_pass and criterion_3_pass
    if passes_formal_threshold:
        status = "pass"
    elif criterion_1_pass and criterion_2_pass:
        status = "primary-supported-secondary-failed"
    else:
        status = "not-passed"

    return {
        "status": status,
        "passes_formal_threshold": passes_formal_threshold,
        "criteria": {
            "criterion_1_exact_win_rate": {
                "passed": criterion_1_pass,
                "required_baselines": required_baselines,
                "threshold": exact_threshold,
                "paired_exact_match_win_rate": win_rates,
            },
            "criterion_2_mean_accuracy_gain": {
                "passed": criterion_2_pass,
                "baseline_mean_accuracy_gain": mean_accuracy_gain,
                "paired_mean_pixel_accuracy_gain": acc_gains,
            },
            "criterion_3_secondary_endpoints": {
                "passed": criterion_3_pass,
                "shared_compression": {
                    "metric": "mean_top1_train_j_score",
                    "direction": "lower_is_better",
                    "multi_preorder": multi_preorder_summary["mean_top1_train_j_score"],
                    "baseline_average": baseline_mean_top1_train_j_score,
                    "relation": shared_compression_relation,
                },
                "robustness": {
                    "metric": "robust_equivalence_rate",
                    "direction": "higher_is_better",
                    "multi_preorder": multi_preorder_summary["robust_equivalence_rate"],
                    "baseline_average": baseline_mean_robustness,
                    "relation": robustness_relation,
                },
            },
        },
    }


def compare_secondary_endpoint(value: float, baseline_average: float, lower_is_better: bool) -> str:
    epsilon = 1e-12
    if lower_is_better:
        if value < baseline_average - epsilon:
            return "strictly_better"
        if value <= baseline_average + epsilon:
            return "not_worse"
        return "worse"
    if value > baseline_average + epsilon:
        return "strictly_better"
    if value >= baseline_average - epsilon:
        return "not_worse"
    return "worse"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the multi-preorder minimal validation experiment")
    parser.add_argument("--appendix-a", type=Path, default=DEFAULT_APPENDIX_A)
    parser.add_argument("--appendix-b", type=Path, default=DEFAULT_APPENDIX_B)
    parser.add_argument("--tasks", type=str, default="")
    parser.add_argument("--methods", type=str, default="")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-perturbations", action="store_true")
    parser.add_argument("--max-folds", type=int, default=None)
    return parser.parse_args()


def _apply_color_permutation(task: dict[str, Any]) -> dict[str, Any]:
    non_background_colors = sorted(
        {
            value
            for split_name in ("train", "test")
            for pair in task[split_name]
            for grid_name in ("input", "output")
            if pair.get(grid_name) is not None
            for row in pair[grid_name]
            for value in row
            if value != 0
        }
    )
    if not non_background_colors:
        return task
    mapping = {color: non_background_colors[(index + 1) % len(non_background_colors)] for index, color in enumerate(non_background_colors)}

    def transform(grid: Grid | None) -> Grid | None:
        if grid is None:
            return None
        return [[mapping.get(value, value) for value in row] for row in grid]

    return {
        split_name: tuple({"input": transform(pair["input"]), "output": transform(pair.get("output"))} for pair in task[split_name])
        for split_name in ("train", "test")
    }


def _apply_shift(task: dict[str, Any]) -> dict[str, Any]:
    def transform(grid: Grid | None) -> Grid | None:
        if grid is None:
            return None
        background = resolve_background_color(grid, "top1")
        return shift_grid(grid, dx=1, dy=1, fill_color=background or 0, pad_if_needed=True)

    return {
        split_name: tuple({"input": transform(pair["input"]), "output": transform(pair.get("output"))} for pair in task[split_name])
        for split_name in ("train", "test")
    }


def _blank_prediction(input_grid: Grid, output_grid: Grid) -> Grid:
    output_shape = grid_shape(output_grid)
    if output_shape == grid_shape(input_grid):
        return [[0 for _ in range(output_shape[1])] for _ in range(output_shape[0])]
    return [[0]]


def _serialize_candidate(candidate: CandidateExplanation) -> dict[str, Any]:
    return {
        "name": candidate.debug_name,
        "sigma": candidate.sigma,
        "train_exact_rate": candidate.train_exact_rate,
        "train_accuracy": candidate.train_accuracy,
        "train_residual_loss": candidate.train_residual_loss,
        "train_program_complexity": candidate.train_program_complexity,
        "train_hypothesis_complexity": candidate.train_hypothesis_complexity,
        "train_j_score": candidate.train_j_score,
    }


def _parse_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _task_console_line(task_report: dict[str, Any], methods: list[str]) -> str:
    gate = task_report["gate"]
    gate_text = "gate-ok" if gate["label_matches_entry"] and gate["train_pair_count_matches"] else "gate-warn"
    parts = [f"{task_report['task_id']} {gate_text}"]
    for method in methods:
        aggregate = task_report["aggregate"][method]
        parts.append(
            f"{method}: exact={int(aggregate['task_exact_match'])} acc={aggregate['mean_pixel_accuracy']:.3f}"
        )
    return " | ".join(parts)


if __name__ == "__main__":
    main()
