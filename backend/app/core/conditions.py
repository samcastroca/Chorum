"""Evaluación segura de condiciones declarativas contra el estado del grafo.

Las condiciones (`Comparison` / `ConditionGroup`) provienen del ``GraphDefinition`` que a su
vez viene de JSON del usuario. Por eso este módulo **nunca** usa ``eval``/``exec``: solo
lectura de campos por *dotted path* y comparaciones de Python. Esto mantiene el ruteo
condicional fuera de cualquier vía de ejecución de código arbitrario.
"""

from __future__ import annotations

from typing import Any

from app.core.schema import Comparison, ConditionGroup, EdgeCondition


class _Missing:
    """Sentinel para 'campo ausente en el estado' (distinto de un valor ``None`` real)."""


_MISSING = _Missing()


def evaluate(condition: EdgeCondition, state: dict[str, Any]) -> bool:
    """Evalúa un ``EdgeCondition`` contra ``state`` y devuelve un booleano."""
    if isinstance(condition, Comparison):
        return _eval_comparison(condition, state)
    return _eval_group(condition, state)


def _get(state: dict[str, Any], dotted: str) -> Any:
    """Lee ``dotted`` (ej. ``"result.ok"``) del estado; devuelve ``_MISSING`` si no existe."""
    current: Any = state
    for part in dotted.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def _eval_comparison(comparison: Comparison, state: dict[str, Any]) -> bool:
    value = _get(state, comparison.field)
    op = comparison.op
    present = value is not _MISSING

    # Operadores que tienen semántica definida incluso con el campo ausente.
    if op == "exists":
        return present
    if op == "falsy":
        return (not bool(value)) if present else True
    if op == "truthy":
        return bool(value) if present else False
    if op == "ne":
        return (not present) or bool(value != comparison.value)
    if op == "not_in":
        return (not present) or _safe_contains(comparison.value, value) is False

    # El resto requiere que el campo exista.
    if not present:
        return False
    if op == "eq":
        return bool(value == comparison.value)
    if op == "in":
        return _safe_contains(comparison.value, value) is True
    if op == "contains":
        return _safe_contains(value, comparison.value) is True
    # Comparaciones de orden: si los tipos no son comparables, la condición es False.
    try:
        if op == "gt":
            return bool(value > comparison.value)
        if op == "gte":
            return bool(value >= comparison.value)
        if op == "lt":
            return bool(value < comparison.value)
        if op == "lte":
            return bool(value <= comparison.value)
    except TypeError:
        return False
    raise ValueError(f"Operador de condición no soportado: {op!r}")


def _safe_contains(container: Any, item: Any) -> bool:
    """``item in container`` tolerante: devuelve ``False`` si el contenedor no lo soporta."""
    try:
        return bool(item in container)
    except TypeError:
        return False


def _eval_group(group: ConditionGroup, state: dict[str, Any]) -> bool:
    """Combina ``all``/``any``/``not`` con AND entre sí (grupo vacío = ``True``)."""
    result = True
    if group.all is not None:
        result = result and all(evaluate(sub, state) for sub in group.all)
    if group.any is not None:
        result = result and any(evaluate(sub, state) for sub in group.any)
    if group.not_ is not None:
        result = result and not evaluate(group.not_, state)
    return result
