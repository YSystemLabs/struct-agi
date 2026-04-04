from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, set):
        return [_normalize(item) for item in sorted(value)]
    if isinstance(value, Path):
        return str(value)
    return value


def dump_json(path: str | Path, payload: dict | list) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(_normalize(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def dump_task_debug_bundle(task_id: str, output_dir: str | Path, bundle: dict) -> None:
    base_dir = Path(output_dir) / "debug" / task_id
    base_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in bundle.items():
        dump_json(base_dir / f"{name}.json", payload)
