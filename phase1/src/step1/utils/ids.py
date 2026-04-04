from __future__ import annotations


def make_plan_id(method: str) -> str:
    return method


def make_alignment_id(plan_id: str, method: str, pair_index: int) -> str:
    return f"{plan_id}:{method}:{pair_index}"


def make_alignment_family_id(plan_id: str, method: str) -> str:
    return f"{plan_id}:{method}"


def _make_scoped_child_id(alignment_key: str, kind: str, local_index: int) -> str:
    return f"{alignment_key}:{kind}:{local_index}"


def make_pair_transform_id(alignment_id: str, local_index: int) -> str:
    return _make_scoped_child_id(alignment_id, "transform", local_index)


def make_family_transform_id(alignment_family_id: str, local_index: int) -> str:
    return _make_scoped_child_id(alignment_family_id, "transform", local_index)


def make_pair_constraint_id(alignment_id: str, local_index: int) -> str:
    return _make_scoped_child_id(alignment_id, "constraint", local_index)


def make_family_constraint_id(alignment_family_id: str, local_index: int) -> str:
    return _make_scoped_child_id(alignment_family_id, "constraint", local_index)


def make_transform_id(alignment_key: str, local_index: int) -> str:
    return _make_scoped_child_id(alignment_key, "transform", local_index)


def make_constraint_id(alignment_key: str, local_index: int) -> str:
    return _make_scoped_child_id(alignment_key, "constraint", local_index)
