"""Tests del constructor del tipo de estado dinámico."""

from __future__ import annotations

import operator
from typing import Annotated, get_args, get_origin, get_type_hints

from app.core.schema import StateChannel
from app.core.state import build_state_type


def test_append_channel_uses_add_reducer() -> None:
    state_type = build_state_type([StateChannel(name="log", type="list", reducer="append")])
    hints = get_type_hints(state_type, include_extras=True)
    annotated = hints["log"]
    assert get_origin(annotated) is Annotated
    # El metadato del Annotated es el reducer operator.add.
    assert operator.add in get_args(annotated)[1:]


def test_replace_channel_uses_plain_type() -> None:
    state_type = build_state_type([StateChannel(name="score", type="int")])
    hints = get_type_hints(state_type, include_extras=True)
    assert hints["score"] is int


def test_empty_schema_gets_default_messages_channel() -> None:
    state_type = build_state_type([])
    hints = get_type_hints(state_type, include_extras=True)
    assert "messages" in hints
