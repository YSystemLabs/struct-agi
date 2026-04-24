from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PrimaryTaskEntry:
    task_id: str
    split: str
    train_pairs: int
    observed_label: str
    template_family: str
    output_size_mode: str
    evidence_flags: tuple[str, ...]


@dataclass(frozen=True)
class AppendixAConfig:
    schema_version: str
    experiment_id: str
    source_doc: str
    dataset: dict[str, Any]
    selection_policy: dict[str, Any]
    primary_tasks: tuple[PrimaryTaskEntry, ...]
    reserve_tasks: tuple[dict[str, Any], ...]
    explicit_exclusions: tuple[dict[str, Any], ...]
    usage_constraints: tuple[str, ...]

    @property
    def dataset_dir(self) -> Path:
        return Path(self.dataset["source_dir"])


@dataclass(frozen=True)
class AppendixBConfig:
    schema_version: str
    experiment_id: str
    source_doc: str
    comparison_methods: tuple[str, ...]
    protocol: dict[str, Any]
    observable_task_gate: dict[str, Any]
    preorder_whitelist: tuple[str, ...]
    global_constants: dict[str, Any]
    features: tuple[dict[str, Any], ...]
    rank_buckets: tuple[dict[str, Any], ...]
    weight_grid: dict[str, tuple[float, ...]]
    whitelists: dict[str, tuple[str, ...]]
    signature: dict[str, Any]
    perturbations: tuple[dict[str, Any], ...]
    search_bounds: dict[str, Any]
    evaluation: dict[str, Any]
    implementation_constraints: tuple[str, ...]

    @property
    def feature_by_id(self) -> dict[str, dict[str, Any]]:
        return {feature["id"]: feature for feature in self.features}


def load_appendix_a(path: Path) -> AppendixAConfig:
    payload = _load_json(path)
    primary_tasks = tuple(
        PrimaryTaskEntry(
            task_id=item["task_id"],
            split=item["split"],
            train_pairs=int(item["train_pairs"]),
            observed_label=item["observed_label"],
            template_family=item["template_family"],
            output_size_mode=item["output_size_mode"],
            evidence_flags=tuple(item.get("evidence_flags", [])),
        )
        for item in payload.get("primary_tasks", [])
    )
    return AppendixAConfig(
        schema_version=str(payload["schema_version"]),
        experiment_id=str(payload["experiment_id"]),
        source_doc=str(payload["source_doc"]),
        dataset=dict(payload["dataset"]),
        selection_policy=dict(payload["selection_policy"]),
        primary_tasks=primary_tasks,
        reserve_tasks=tuple(dict(item) for item in payload.get("reserve_tasks", [])),
        explicit_exclusions=tuple(dict(item) for item in payload.get("explicit_exclusions", [])),
        usage_constraints=tuple(str(item) for item in payload.get("usage_constraints", [])),
    )


def load_appendix_b(path: Path) -> AppendixBConfig:
    payload = _load_json(path)
    return AppendixBConfig(
        schema_version=str(payload["schema_version"]),
        experiment_id=str(payload["experiment_id"]),
        source_doc=str(payload["source_doc"]),
        comparison_methods=tuple(payload["comparison_methods"]),
        protocol=dict(payload["protocol"]),
        observable_task_gate=dict(payload["observable_task_gate"]),
        preorder_whitelist=tuple(payload["preorder_whitelist"]),
        global_constants=dict(payload["global_constants"]),
        features=tuple(dict(item) for item in payload["features"]),
        rank_buckets=tuple(dict(item) for item in payload["rank_buckets"]),
        weight_grid={key: tuple(value) for key, value in payload["weight_grid"].items()},
        whitelists={key: tuple(value) for key, value in payload["whitelists"].items()},
        signature=dict(payload["signature"]),
        perturbations=tuple(dict(item) for item in payload["perturbations"]),
        search_bounds=dict(payload["search_bounds"]),
        evaluation=dict(payload["evaluation"]),
        implementation_constraints=tuple(payload["implementation_constraints"]),
    )


def load_arc_task(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    return {
        "train": tuple({"input": pair["input"], "output": pair["output"]} for pair in payload.get("train", [])),
        "test": tuple({"input": pair["input"], "output": pair.get("output")} for pair in payload.get("test", [])),
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
