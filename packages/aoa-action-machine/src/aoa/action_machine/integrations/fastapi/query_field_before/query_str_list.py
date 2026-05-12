# packages/aoa-action-machine/src/aoa/action_machine/integrations/fastapi/query_field_before/query_str_list.py
"""
Query array → ``list[str]`` coercion (OpenAPI ``explode``, no delimiter splitting).

AI-CORE-BEGIN
ROLE: Normalize FastAPI query inputs into a clean ``list[str]`` before Pydantic validates ``list[str]``.
CONTRACT: ``None`` / ``""`` → ``[]``; ``str`` → at most one token (strip only); ``list`` / ``tuple`` → strip each item, drop empties.
INVARIANTS: Does not split on commas or other delimiters inside values.
AI-CORE-END
"""

from __future__ import annotations

from functools import partial

from pydantic import BeforeValidator


def coerce_query_str_list(value: object) -> list[str]:
    """
    Normalize a query-style value to ``list[str]`` without delimiter splitting.

    Args:
        value: ``None``, empty string, one non-empty string, or a sequence of values coercible to ``str``.

    Returns:
        List of stripped non-empty strings, order preserved.

    Raises:
        TypeError: If ``value`` is not ``None``, ``str``, ``list``, or ``tuple``.
    """
    if value is None or value == "":
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    msg = f"expected None, str, list, or tuple, got {type(value).__name__}"
    raise TypeError(msg)


#: Repeated query keys / one string token per value (see :func:`coerce_query_str_list`).
QUERY_STR_LIST_BEFORE = BeforeValidator(partial(coerce_query_str_list))
