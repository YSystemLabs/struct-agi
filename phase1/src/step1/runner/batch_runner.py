from __future__ import annotations

from collections import Counter
from pathlib import Path

from phase1.src.step1.config import DEFAULT_OUTPUT_DIR
from phase1.src.step1.data.loader import load_step1_train_tasks
from phase1.src.step1.data.models import Attribution, to_jsonable
from phase1.src.step1.runner.task_runner import run_task
from phase1.src.step1.utils.debug_dump import dump_json


def run_step1_batch(output_dir: str | Path) -> list[Attribution]:
    tasks = load_step1_train_tasks()
    return [run_task(task, output_dir) for task in tasks]


def build_summary(attributions: list[Attribution]) -> dict:
    failure_counts = Counter(item.failure_type for item in attributions)
    plan_counts = Counter(item.selected_plan for item in attributions if item.selected_plan)
    alignment_methods = Counter(
        item.selected_alignment_family.split(":")[1]
        for item in attributions
        if item.selected_alignment_family
    )
    summary = {
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
    }
    return summary


def main() -> None:
    output_dir = Path(DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    attributions = run_step1_batch(output_dir)
    summary = build_summary(attributions)
    dump_json(reports_dir / "summary.json", summary)
    (reports_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    dump_json(reports_dir / "attributions.json", to_jsonable(attributions))


def _render_summary_markdown(summary: dict) -> str:
    lines = ["# Step 1 Summary", "", f"- exact_solved: {summary['exact_solved']}"]
    lines.append(f"- most_selected_plan: {summary['most_selected_plan']}")
    lines.append(f"- most_selected_alignment_strategy: {summary['most_selected_alignment_strategy']}")
    lines.append("- failure_type_distribution:")
    for name, count in summary["failure_type_distribution"].items():
        lines.append(f"  - {name}: {count}")
    lines.append("- average_layer_times_ms:")
    for name, value in summary["average_layer_times_ms"].items():
        lines.append(f"  - {name}: {value}")
    return "\n".join(lines) + "\n"


def _average(values: list[int]) -> float:
    return 0.0 if not values else round(sum(values) / len(values), 3)


if __name__ == "__main__":
    main()
