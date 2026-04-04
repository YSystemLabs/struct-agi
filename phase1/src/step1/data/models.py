from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any


Grid = list[list[int]]
Cell = tuple[int, int]
RelationEdge = tuple[str, str, str]


def _normalize_json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: _normalize_json_value(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, dict):
        return {
            str(key): _normalize_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, set):
        return [_normalize_json_value(item) for item in sorted(value)]
    if isinstance(value, Path):
        return str(value)
    return value


@dataclass(frozen=True)
class ExamplePair:
    pair_index: int
    split: str
    input: Grid
    output: Grid | None

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class ArcTask:
    task_id: str
    concept: str
    file_path: str
    train_pairs: list[ExamplePair]
    test_pairs: list[ExamplePair]

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class ObjectData:
    id: str
    pixels: set[Cell]
    bbox: tuple[int, int, int, int]
    attrs: dict[str, int | float]

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class SegmentationPlan:
    plan_id: str
    method: str
    objects: list[ObjectData]
    relations: list[RelationEdge]

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class PerceptionOutput:
    segmentation_plans: list[SegmentationPlan]

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class Alignment:
    alignment_id: str
    alignment_family_id: str
    matched_pairs: list[tuple[str, str, float]]
    unmatched_input: list[str]
    unmatched_output: list[str]
    merge_groups: list[list[str]]
    split_groups: list[list[str]]

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class CandidateTransform:
    transform_id: str
    alignment_id: str
    alignment_family_id: str
    program: object
    applicable_pairs: list[int]
    match_score: float

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class CandidateConstraint:
    constraint_id: str
    alignment_id: str
    alignment_family_id: str
    predicate: str
    holds_in: list[int]

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class CandidateSet:
    plan_id: str
    candidate_alignments: list[Alignment]
    candidate_transforms: list[CandidateTransform]
    candidate_constraints: list[CandidateConstraint]

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class Hypothesis:
    plan_id: str
    alignment_id: str
    alignment_family_id: str
    constraint_subset: dict[str, list[str]]
    program: str

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class SearchStats:
    candidates_generated: int
    candidates_evaluated: int
    search_time_ms: int
    beam_saturated: bool
    layer1_time_ms: int
    layer2_time_ms: int
    layer3_time_ms: int
    layer4_time_ms: int
    layer5_time_ms: int

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


@dataclass(frozen=True)
class Attribution:
    task_id: str
    eval_mode: str
    success: bool
    pixel_accuracy: float
    failure_type: str
    failure_detail: str | None
    selected_plan: str
    selected_alignment: str
    selected_alignment_family: str
    selected_program: str
    selected_constraints: dict[str, list[str]]
    search_stats: SearchStats

    def to_dict(self) -> dict[str, Any]:
        return _normalize_json_value(self)


def to_jsonable(value: Any) -> Any:
    return _normalize_json_value(value)
