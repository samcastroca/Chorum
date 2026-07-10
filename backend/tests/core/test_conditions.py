"""Tests de la evaluación de condiciones declarativas (sin ``eval``)."""

from __future__ import annotations

from typing import Any

import pytest

from app.core.conditions import evaluate
from app.core.schema import Comparison, ConditionGroup


@pytest.mark.parametrize(
    ("op", "value", "state", "expected"),
    [
        ("eq", 5, {"x": 5}, True),
        ("eq", 5, {"x": 6}, False),
        ("ne", 5, {"x": 6}, True),
        ("ne", 5, {}, True),  # ausente != valor -> True
        ("gt", 3, {"x": 5}, True),
        ("gt", 3, {"x": 3}, False),
        ("gte", 3, {"x": 3}, True),
        ("lt", 3, {"x": 2}, True),
        ("lte", 3, {"x": 3}, True),
        ("in", [1, 2, 3], {"x": 2}, True),
        ("in", [1, 2, 3], {"x": 9}, False),
        ("not_in", [1, 2, 3], {"x": 9}, True),
        ("not_in", [1, 2, 3], {}, True),  # ausente -> not_in True
        ("contains", "b", {"x": ["a", "b"]}, True),
        ("contains", "z", {"x": ["a", "b"]}, False),
        ("truthy", None, {"x": 1}, True),
        ("truthy", None, {"x": 0}, False),
        ("truthy", None, {}, False),
        ("falsy", None, {"x": 0}, True),
        ("falsy", None, {}, True),  # ausente es falsy
        ("exists", None, {"x": None}, True),
        ("exists", None, {}, False),
    ],
)
def test_comparison_operators(op: str, value: Any, state: dict[str, Any], expected: bool) -> None:
    assert evaluate(Comparison(field="x", op=op, value=value), state) is expected


def test_incomparable_order_is_false_not_error() -> None:
    # str vs int no es comparable con > : la condición debe ser False, no explotar.
    assert evaluate(Comparison(field="x", op="gt", value=3), {"x": "hola"}) is False


def test_dotted_path_access() -> None:
    state = {"result": {"ok": True, "score": 7}}
    assert evaluate(Comparison(field="result.ok", op="truthy"), state) is True
    assert evaluate(Comparison(field="result.score", op="gte", value=7), state) is True
    assert evaluate(Comparison(field="result.missing", op="exists"), state) is False


def test_group_all_any_not() -> None:
    state = {"a": 5, "b": 2}
    all_true = ConditionGroup(
        all=[Comparison(field="a", op="gt", value=1), Comparison(field="b", op="lt", value=3)]
    )
    assert evaluate(all_true, state) is True

    any_group = ConditionGroup(
        any=[Comparison(field="a", op="gt", value=100), Comparison(field="b", op="eq", value=2)]
    )
    assert evaluate(any_group, state) is True

    not_group = ConditionGroup(not_=Comparison(field="a", op="eq", value=5))
    assert evaluate(not_group, state) is False


def test_nested_groups() -> None:
    state = {"a": 5, "b": 2}
    nested = ConditionGroup(
        all=[
            ConditionGroup(any=[Comparison(field="a", op="eq", value=5)]),
            ConditionGroup(not_=Comparison(field="b", op="gt", value=10)),
        ]
    )
    assert evaluate(nested, state) is True


def test_empty_group_is_true() -> None:
    assert evaluate(ConditionGroup(), {}) is True
