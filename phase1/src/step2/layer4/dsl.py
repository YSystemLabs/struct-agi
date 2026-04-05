from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phase1.src.step2.config import ALLOWED_PRIMITIVES


FORBIDDEN_TOKENS = (
    "ForEach",
    "If",
    "group_by",
    "merge",
    "partition",
    "construct_grid",
)


@dataclass(frozen=True)
class PrimitiveCall:
    op: str
    target: str = "all"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CopyClause:
    primitives: tuple[PrimitiveCall, ...] = ()


@dataclass(frozen=True)
class CopyBlock:
    on_copy: CopyClause = field(default_factory=CopyClause)
    on_original: CopyClause = field(default_factory=CopyClause)
    target: str = "all"


@dataclass(frozen=True)
class Step1Program:
    primitives: tuple[PrimitiveCall, ...] = ()
    copy_block: CopyBlock | None = None


def _format_params(params: dict[str, Any]) -> str:
    if not params:
        return ""
    return "," + ",".join(f"{key}={params[key]}" for key in sorted(params))


def _render_primitive(primitive: PrimitiveCall) -> str:
    return f"{primitive.op}[target={primitive.target}{_format_params(primitive.params)}]"


def render_program(program: Step1Program) -> str:
    validate_step1_program(program)
    parts = [_render_primitive(primitive) for primitive in program.primitives]
    if program.copy_block is not None:
        parts.append("copy[target={}]".format(program.copy_block.target))
        on_copy = "; ".join(_render_primitive(item) for item in program.copy_block.on_copy.primitives)
        on_original = "; ".join(
            _render_primitive(item) for item in program.copy_block.on_original.primitives
        )
        parts.append(f"on_copy: {on_copy}" if on_copy else "on_copy:")
        parts.append(f"on_original: {on_original}" if on_original else "on_original:")
    return " ; ".join(parts)


def parse_program(program_text: str) -> Step1Program:
    if not program_text.strip():
        return Step1Program()

    parts = [part.strip() for part in program_text.split(" ; ") if part.strip()]
    primitives: list[PrimitiveCall] = []
    copy_block: CopyBlock | None = None
    index = 0
    while index < len(parts):
        part = parts[index]
        if part.startswith("copy["):
            target = _parse_primitive(part).target
            on_copy = CopyClause()
            on_original = CopyClause()
            if index + 1 < len(parts) and parts[index + 1].startswith("on_copy:"):
                on_copy = CopyClause(primitives=_parse_clause(parts[index + 1]))
                index += 1
            if index + 1 < len(parts) and parts[index + 1].startswith("on_original:"):
                on_original = CopyClause(primitives=_parse_clause(parts[index + 1]))
                index += 1
            copy_block = CopyBlock(on_copy=on_copy, on_original=on_original, target=target)
        else:
            primitives.append(_parse_primitive(part))
        index += 1

    program = Step1Program(primitives=tuple(primitives), copy_block=copy_block)
    validate_step1_program(program)
    return program


def validate_step1_program(program: Step1Program) -> None:
    def validate_primitive(primitive: PrimitiveCall) -> None:
        if primitive.op not in ALLOWED_PRIMITIVES:
            raise ValueError(f"Unsupported primitive in Step 1: {primitive.op}")
        for token in FORBIDDEN_TOKENS:
            if token in primitive.op or token in primitive.target:
                raise ValueError(f"Forbidden control semantics in Step 1 program: {token}")
        for value in primitive.params.values():
            if isinstance(value, str):
                for token in FORBIDDEN_TOKENS:
                    if token in value:
                        raise ValueError(f"Forbidden control semantics in Step 1 program: {token}")

    for primitive in program.primitives:
        validate_primitive(primitive)

    if any(primitive.op == "copy" for primitive in program.primitives):
        raise ValueError("copy must be expressed via CopyBlock, not as a bare primitive")

    if program.copy_block is not None:
        for primitive in program.copy_block.on_copy.primitives:
            validate_primitive(primitive)
        for primitive in program.copy_block.on_original.primitives:
            validate_primitive(primitive)


def _parse_clause(text: str) -> tuple[PrimitiveCall, ...]:
    _, payload = text.split(":", 1)
    payload = payload.strip()
    if not payload:
        return ()
    return tuple(_parse_primitive(part.strip()) for part in payload.split("; ") if part.strip())


def _parse_primitive(text: str) -> PrimitiveCall:
    name, payload = text.split("[", 1)
    payload = payload[:-1]
    params: dict[str, Any] = {}
    target = "all"
    for entry in payload.split(","):
        key, raw_value = entry.split("=", 1)
        value = _parse_value(raw_value)
        if key == "target":
            target = str(value)
        else:
            params[key] = value
    return PrimitiveCall(op=name, target=target, params=params)


def _parse_value(raw_value: str) -> Any:
    raw_value = raw_value.strip()
    if raw_value.lstrip("-").isdigit():
        return int(raw_value)
    return raw_value
