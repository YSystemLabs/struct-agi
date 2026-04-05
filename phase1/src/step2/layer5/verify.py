from __future__ import annotations

from phase1.src.step2.data.models import Grid, Hypothesis


def pixel_accuracy(predicted: Grid, target: Grid) -> float:
    total = 0
    matched = 0
    max_rows = max(len(predicted), len(target))
    max_cols = max(len(predicted[0]), len(target[0])) if predicted and target else 0
    for row in range(max_rows):
        for col in range(max_cols):
            total += 1
            predicted_value = predicted[row][col] if row < len(predicted) and col < len(predicted[0]) else -1
            target_value = target[row][col] if row < len(target) and col < len(target[0]) else -1
            if predicted_value == target_value:
                matched += 1
    return 1.0 if total == 0 else matched / total


def verify_constraints(predicted: Grid, hypothesis: Hypothesis) -> tuple[list[str], list[str]]:
    satisfied: list[str] = []
    violated: list[str] = []
    for predicate in hypothesis.constraint_subset.get("strong", []):
        if predicate.startswith("size_rule:crop_center_cell") and (len(predicted), len(predicted[0])) != (1, 1):
            violated.append(predicate)
        else:
            satisfied.append(predicate)
    return (satisfied, violated)


def classify_failure(
    has_perception: bool,
    has_hypothesis: bool,
    execution_ok: bool,
    exact_match: bool,
) -> str:
    if exact_match:
        return "NONE"
    if not has_perception:
        return "PERCEPTION_FAIL"
    if not has_hypothesis:
        return "SELECTION_FAIL"
    if not execution_ok:
        return "EXECUTION_FAIL"
    return "ABSTRACTION_FAIL"
