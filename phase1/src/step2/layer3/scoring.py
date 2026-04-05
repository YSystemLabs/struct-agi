from __future__ import annotations

import re

from phase1.src.step2.data.models import Grid, Hypothesis
from phase1.src.step2.layer4.dsl import parse_program


def description_length(hypothesis: Hypothesis) -> int:
    """§5.3.2 L(h) = 分割方案数 + AST节点数 + 强约束数 + 常量数"""
    # 分割方案数（Step 1 固定为 1）
    plan_count = 1
    # AST 节点数
    program = parse_program(hypothesis.program)
    ast_node_count = len(program.primitives)
    if program.copy_block is not None:
        ast_node_count += 1  # CopyBlock 本身
        ast_node_count += len(program.copy_block.on_copy.primitives)
        ast_node_count += len(program.copy_block.on_original.primitives)
    # 强约束数（弱约束不计入）
    strong_constraints = hypothesis.constraint_subset.get("strong", [])
    # 具体常量数（引用对象属性的不计入）
    constant_count = len(re.findall(r"-?\d+", hypothesis.program))
    return plan_count + ast_node_count + len(strong_constraints) + constant_count


_SYMBOLIC_PARAM_TOKENS = {"input_width", "input_height", "object_width", "object_height"}


def pre_priority(hypothesis: Hypothesis) -> tuple[float, int]:
    token_count = max(1, len([token for token in re.split(r"[^A-Za-z_]+", hypothesis.program) if token]))
    attr_ref_count = hypothesis.program.count("target=") + hypothesis.program.count("color=") + hypothesis.program.count("mode=")
    # 符号参数引用输入/对象属性，也应计为属性引用
    for token in re.split(r"[^A-Za-z_]+", hypothesis.program):
        if token in _SYMBOLIC_PARAM_TOKENS:
            attr_ref_count += 1
    attr_ref_ratio = attr_ref_count / token_count
    attr_ref_ratio += _semantic_consistency_bonus(hypothesis.program)
    # 排除 copy block 结构性分隔符，只计真实语句深度
    stmt_separators = hypothesis.program.count(";") - hypothesis.program.count("on_copy:") - hypothesis.program.count("on_original:")
    ast_depth = max(1, stmt_separators + 1)
    return (-attr_ref_ratio, ast_depth)


def _semantic_consistency_bonus(program_text: str) -> float:
    bonus = 0.0
    if "copy[" in program_text:
        bonus += 0.35
    elif program_text.startswith("delete["):
        bonus += 0.15
    elif program_text.startswith("translate["):
        bonus += 0.15
    elif program_text.startswith("crop["):
        bonus += 0.15
    return bonus


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
