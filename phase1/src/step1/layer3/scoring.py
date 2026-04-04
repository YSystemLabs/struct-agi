from __future__ import annotations

import re

from phase1.src.step1.data.models import Grid, Hypothesis


def description_length(hypothesis: Hypothesis) -> int:
    strong_constraints = hypothesis.constraint_subset.get("strong", [])
    constant_count = len(re.findall(r"-?\d+", hypothesis.program))
    return len(hypothesis.program) + (8 * len(strong_constraints)) + constant_count


def pre_priority(hypothesis: Hypothesis) -> tuple[float, int]:
    token_count = max(1, len([token for token in re.split(r"[^A-Za-z_]+", hypothesis.program) if token]))
    attr_ref_count = hypothesis.program.count("target=") + hypothesis.program.count("color=")
    attr_ref_ratio = attr_ref_count / token_count
    ast_depth = max(1, hypothesis.program.count(";") + 1)
    return (-attr_ref_ratio, ast_depth)


def mismatch_sum(outputs: list[Grid], targets: list[Grid]) -> int:
    total = 0
    for index in range(max(len(outputs), len(targets))):
        predicted = outputs[index] if index < len(outputs) else []
        target = targets[index] if index < len(targets) else []
        max_rows = max(len(predicted), len(target))
        max_cols = max(
            len(predicted[0]) if predicted else 0,
            len(target[0]) if target else 0,
        )
        for row in range(max_rows):
            for col in range(max_cols):
                predicted_value = predicted[row][col] if row < len(predicted) and col < len(predicted[0]) else -1
                target_value = target[row][col] if row < len(target) and col < len(target[0]) else -1
                if predicted_value != target_value:
                    total += 1
    return total
