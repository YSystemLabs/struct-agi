from __future__ import annotations

import json
from json import JSONDecodeError

from phase1.src.step2.config import STEP2_TRAIN_TASKS
from phase1.src.step2.data.models import ArcTask, ExamplePair, Grid


def _validate_grid(grid: Grid | None, file_path: str, split: str, pair_index: int) -> Grid | None:
    if grid is None:
        return None
    if not isinstance(grid, list) or not grid or not all(isinstance(row, list) for row in grid):
        raise ValueError(
            f"Invalid grid in {file_path} ({split}[{pair_index}]): expected non-empty 2D list"
        )
    widths = {len(row) for row in grid}
    if len(widths) != 1:
        raise ValueError(
            f"Invalid grid in {file_path} ({split}[{pair_index}]): ragged rows are not allowed"
        )
    return grid


def _parse_pairs(raw_pairs: list[dict], split: str, file_path: str) -> list[ExamplePair]:
    parsed: list[ExamplePair] = []
    for pair_index, pair in enumerate(raw_pairs):
        input_grid = _validate_grid(pair.get("input"), file_path, split, pair_index)
        output_grid = _validate_grid(pair.get("output"), file_path, split, pair_index)
        if input_grid is None:
            raise ValueError(f"Missing input grid in {file_path} ({split}[{pair_index}])")
        parsed.append(
            ExamplePair(
                pair_index=pair_index,
                split=split,
                input=input_grid,
                output=output_grid,
            )
        )
    return parsed


def load_task(concept: str, task_id: str, file_path: str) -> ArcTask:
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON file {file_path}: {exc}") from exc
    except OSError as exc:
        raise OSError(f"Failed to read task file {file_path}: {exc}") from exc

    train_pairs = _parse_pairs(raw.get("train", []), "train", file_path)
    test_pairs = _parse_pairs(raw.get("test", []), "test", file_path)
    return ArcTask(
        task_id=task_id,
        concept=concept,
        file_path=file_path,
        train_pairs=train_pairs,
        test_pairs=test_pairs,
    )


def load_step2_train_tasks() -> list[ArcTask]:
    return [load_task(concept, task_id, file_path) for concept, task_id, file_path in STEP2_TRAIN_TASKS]


def load_step2_task_ids() -> list[str]:
    return [task_id for _, task_id, _ in STEP2_TRAIN_TASKS]
