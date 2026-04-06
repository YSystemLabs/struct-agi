from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from phase1.src.step2.config import DEFAULT_OUTPUT_DIR, STEP2_CONCEPT_GROUPS
from phase1.src.step2.data.loader import load_step2_train_tasks
from phase1.src.step2.data.models import Attribution, to_jsonable
from phase1.src.step2.runner.task_runner import run_task
from phase1.src.step2.utils.debug_dump import dump_json


STEP2A_CONCEPT_GROUPS = {"Copy", "Center"}
STEP2B_CONCEPT_GROUPS = {"MoveToBoundary", "ExtendToBoundary", "ExtractObjects", "CleanUp"}
FROZEN_UNRESOLVED_GROUPS = {"CleanUp"}
EXPECTED_EXACT_TASKS = {
    "step2a_exact_regression": {"Copy1", "Copy2", "Center1", "Center2", "Center3", "Center4", "Center5", "Center6"},
    "phase7a_exact_regression": {"MoveToBoundary1", "MoveToBoundary3", "MoveToBoundary5"},
    "phase7b_exact_regression": {"ExtendToBoundary2", "ExtendToBoundary4"},
    "phase7c_exact_regression": {"ExtractObjects1", "ExtractObjects3"},
}


def run_step2_batch(output_dir: str | Path, stage: str | None = None, group: str | None = None) -> list[Attribution]:
    tasks = _filter_tasks(load_step2_train_tasks(), stage=stage, group=group)
    return [run_task(task, output_dir) for task in tasks]


def build_summary(attributions: list[Attribution]) -> dict:
    failure_counts = Counter(item.failure_type for item in attributions)
    plan_counts = Counter(item.selected_plan for item in attributions if item.selected_plan)
    alignment_methods = Counter(
        item.selected_alignment_family.split(":")[1]
        for item in attributions
        if item.selected_alignment_family
    )
    regression_flags = build_regression_flags(attributions)
    summary = {
        "task_count": len(attributions),
        "exact_solved": sum(1 for item in attributions if item.success),
        "failure_type_distribution": dict(sorted(failure_counts.items())),
        "average_layer_times_ms": {
            "layer1": _average([item.search_stats.layer1_time_ms for item in attributions]),
            "layer2": _average([item.search_stats.layer2_time_ms for item in attributions]),
            "layer3": _average([item.search_stats.layer3_time_ms for item in attributions]),
            "layer4": _average([item.search_stats.layer4_time_ms for item in attributions]),
            "layer5": _average([item.search_stats.layer5_time_ms for item in attributions]),
        },
        "most_selected_plan": plan_counts.most_common(1)[0][0] if plan_counts else "",
        "most_selected_alignment_strategy": alignment_methods.most_common(1)[0][0] if alignment_methods else "",
        "concept_group_summary": _build_concept_group_summary(attributions),
        "regression_flag_distribution": dict(sorted(Counter(flag for flags in regression_flags.values() for flag in flags).items())),
        "regression_tasks": {task_id: flags for task_id, flags in sorted(regression_flags.items()) if flags},
        "frozen_unresolved_groups": sorted(FROZEN_UNRESOLVED_GROUPS),
    }
    return summary


def build_regression_flags(attributions: list[Attribution]) -> dict[str, list[str]]:
    flags_by_task: dict[str, list[str]] = {}
    for item in attributions:
        flags: list[str] = []
        if not item.success:
            for flag_name, task_ids in EXPECTED_EXACT_TASKS.items():
                if item.task_id in task_ids:
                    flags.append(flag_name)
        flags_by_task[item.task_id] = flags
    return flags_by_task


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 2 batch evaluation with phase/group filters.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--stage", choices=("2a", "2b", "all"), default="all")
    parser.add_argument("--group", choices=tuple(STEP2_CONCEPT_GROUPS))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    attributions = run_step2_batch(output_dir, stage=args.stage, group=args.group)
    summary = build_summary(attributions)
    summary["filters"] = {"stage": args.stage, "group": args.group or ""}
    dump_json(reports_dir / "summary.json", summary)
    (reports_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    dump_json(reports_dir / "attributions.json", to_jsonable(attributions))
    dump_json(reports_dir / "regression_flags.json", build_regression_flags(attributions))


def _render_summary_markdown(summary: dict) -> str:
    lines = ["# Step 2 Summary", "", f"- task_count: {summary['task_count']}", f"- exact_solved: {summary['exact_solved']}"]
    filters = summary.get("filters", {})
    if filters:
        lines.append(f"- stage_filter: {filters.get('stage', '')}")
        lines.append(f"- group_filter: {filters.get('group', '')}")
    lines.append(f"- most_selected_plan: {summary['most_selected_plan']}")
    lines.append(f"- most_selected_alignment_strategy: {summary['most_selected_alignment_strategy']}")
    lines.append("- failure_type_distribution:")
    for name, count in summary["failure_type_distribution"].items():
        lines.append(f"  - {name}: {count}")
    lines.append("- average_layer_times_ms:")
    for name, value in summary["average_layer_times_ms"].items():
        lines.append(f"  - {name}: {value}")
    lines.append("- concept_group_summary:")
    for group_name, group_summary in summary["concept_group_summary"].items():
        lines.append(
            f"  - {group_name}: exact={group_summary['exact_solved']}/{group_summary['task_count']}, avg_pixel_accuracy={group_summary['average_pixel_accuracy']}"
        )
    lines.append("- regression_flag_distribution:")
    for name, count in summary["regression_flag_distribution"].items():
        lines.append(f"  - {name}: {count}")
    if summary["regression_tasks"]:
        lines.append("- regression_tasks:")
        for task_id, flags in summary["regression_tasks"].items():
            lines.append(f"  - {task_id}: {', '.join(flags)}")
    lines.append(f"- frozen_unresolved_groups: {', '.join(summary['frozen_unresolved_groups'])}")
    return "\n".join(lines) + "\n"


def _average(values: list[int]) -> float:
    return 0.0 if not values else round(sum(values) / len(values), 3)


def _build_concept_group_summary(attributions: list[Attribution]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[Attribution]] = {}
    for item in attributions:
        group_name = item.concept_group or ""
        grouped.setdefault(group_name, []).append(item)

    summary: dict[str, dict[str, object]] = {}
    for group_name, items in sorted(grouped.items()):
        failure_counts = Counter(item.failure_type for item in items)
        summary[group_name] = {
            "task_count": len(items),
            "exact_solved": sum(1 for item in items if item.success),
            "average_pixel_accuracy": round(sum(item.pixel_accuracy for item in items) / len(items), 4),
            "failure_type_distribution": dict(sorted(failure_counts.items())),
        }
    return summary


def _filter_tasks(tasks: list, stage: str | None, group: str | None) -> list:
    filtered = list(tasks)
    if stage and stage != "all":
        allowed_groups = STEP2A_CONCEPT_GROUPS if stage == "2a" else STEP2B_CONCEPT_GROUPS
        filtered = [task for task in filtered if task.concept in allowed_groups]
    if group:
        filtered = [task for task in filtered if task.concept == group]
    return filtered


if __name__ == "__main__":
    main()
