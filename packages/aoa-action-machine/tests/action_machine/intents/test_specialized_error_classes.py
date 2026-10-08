"""Every intent invariant answers with a class of its own, never a Python builtin."""

from __future__ import annotations

import ast
from pathlib import Path

INTENTS_DIR = Path(__file__).resolve().parents[3] / "src" / "aoa" / "action_machine" / "intents"

_BUILTIN = {
    "AssertionError",
    "AttributeError",
    "Exception",
    "IndexError",
    "KeyError",
    "NotImplementedError",
    "RuntimeError",
    "TypeError",
    "ValueError",
}


def _builtin_raises() -> list[str]:
    """Return every ``raise`` of a Python builtin inside ``intents/``."""
    offenders: list[str] = []
    for path in sorted(INTENTS_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            name = ast.unparse(node.exc.func).split(".")[-1]
            if name in _BUILTIN:
                offenders.append(f"{path.relative_to(INTENTS_DIR)}:{node.lineno} raises {name}")
    return offenders


def test_every_intent_invariant_raises_a_specialized_error() -> None:
    """An invariant violation is a named class the caller can catch, not a builtin."""
    offenders = _builtin_raises()
    assert not offenders, "intent invariants must answer with a class of their own:\n" + "\n".join(offenders)
