from __future__ import annotations

from itertools import permutations

from phase1.src.step1.data.models import ObjectData, RelationEdge


def extract_relations(objects: list[ObjectData]) -> list[RelationEdge]:
    relations: set[RelationEdge] = set()
    for source, target in permutations(objects, 2):
        relation = _relative_position(source, target)
        if relation is not None:
            relations.add((source.id, target.id, relation))
        for alignment in _alignment_relations(source, target):
            relations.add((source.id, target.id, alignment))
    return sorted(relations)


def _relative_position(source: ObjectData, target: ObjectData) -> str | None:
    source_row = float(source.attrs["center_row"])
    source_col = float(source.attrs["center_col"])
    target_row = float(target.attrs["center_row"])
    target_col = float(target.attrs["center_col"])
    row_gap = target_row - source_row
    col_gap = target_col - source_col
    if abs(col_gap) >= abs(row_gap) and col_gap > 0:
        return "left_of"
    if abs(col_gap) >= abs(row_gap) and col_gap < 0:
        return "right_of"
    if row_gap > 0:
        return "above"
    if row_gap < 0:
        return "below"
    return None


def _alignment_relations(source: ObjectData, target: ObjectData) -> list[str]:
    relations: list[str] = []
    if source.bbox[0] == target.bbox[0]:
        relations.append("aligned_top")
    if source.bbox[2] == target.bbox[2]:
        relations.append("aligned_bottom")
    if source.bbox[1] == target.bbox[1]:
        relations.append("aligned_left")
    if source.bbox[3] == target.bbox[3]:
        relations.append("aligned_right")
    if source.attrs["center_row"] == target.attrs["center_row"]:
        relations.append("aligned_row_center")
    if source.attrs["center_col"] == target.attrs["center_col"]:
        relations.append("aligned_col_center")
    return relations
