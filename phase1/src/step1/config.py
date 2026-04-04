from __future__ import annotations

from pathlib import Path


PHASE1_ROOT = Path(__file__).resolve().parents[2]
CONCEPT_ARC_ROOT = PHASE1_ROOT / "datasets" / "raw" / "ConceptARC" / "corpus"
DEFAULT_OUTPUT_DIR = str(PHASE1_ROOT / "outputs" / "step1")

ALLOWED_SEGMENTATION_METHODS: tuple[str, ...] = ("cc4", "cc8", "whole_grid")
ALLOWED_PRIMITIVES: tuple[str, ...] = (
    "copy",
    "translate",
    "rotate",
    "flip",
    "delete",
    "recolor",
    "fill",
    "crop",
)
ALLOWED_OUTPUT_SIZE_RULES: tuple[str, ...] = (
    "preserve_input_size",
    "fit_transformed_extent",
    "crop_selected_bbox",
    "crop_center_cell",
)
ALLOWED_FAILURE_TYPES: tuple[str, ...] = (
    "NONE",
    "PERCEPTION_FAIL",
    "SELECTION_FAIL",
    "ABSTRACTION_FAIL",
    "EXECUTION_FAIL",
)
STEP1_BEAM_SIZE = 32


def _task_tuple(concept: str, task_id: str) -> tuple[str, str, str]:
    return (concept, task_id, str(CONCEPT_ARC_ROOT / concept / f"{task_id}.json"))


STEP1_TRAIN_TASKS: list[tuple[str, str, str]] = [
    *[_task_tuple("Copy", f"Copy{i}") for i in range(1, 7)],
    *[_task_tuple("Center", f"Center{i}") for i in range(1, 7)],
]

STEP1_DIAGNOSTIC_TASKS: list[tuple[str, str, str]] = [
    *[_task_tuple("Copy", f"Copy{i}") for i in range(7, 11)],
    *[_task_tuple("Center", f"Center{i}") for i in range(7, 11)],
]
