# src/action_machine/logging/expression_evaluator.py
"""
Expression evaluator for ActionMachine logging templates.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Uses ``simpleeval`` to safely evaluate expressions inside
``{iif(condition; true_value; false_value)}``.

``simpleeval`` does not allow ``import``, ``exec``, ``eval``, ``__builtins__``,
or filesystem/network access. This keeps logging templates from executing
arbitrary code.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    template string
         |
         v
    process_template(...)
         |
         +--> detect {iif(...)} with _IIF_PATTERN
         |         |
         |         v
         |   evaluate_iif(...)
         |      -> _IifArgSplitter
         |      -> evaluate(...) via simpleeval
         |
         v
    rendered string (+ color markers)
         |
         v
    VariableSubstitutor color expansion / final log output

═══════════════════════════════════════════════════════════════════════════════
FEATURES
═══════════════════════════════════════════════════════════════════════════════

- Comparison operators: ``==``, ``!=``, ``>``, ``<``, ``>=``, ``<=``
- Logical operators: ``and``, ``or``, ``not``
- Arithmetic: ``+``, ``-``, ``*``, ``/``
- Safe helpers: ``len``, ``upper``, ``lower``, ``format_number``, ``str``,
  ``int``, ``float``, ``abs``
- Color helpers: ``red``, ``green``, ``yellow``, ``blue``, ``magenta``,
  ``cyan``, ``white``, ``grey``
- ``debug(obj)``: formatted public field/property snapshot
- ``exists(name)``: checks whether a name exists in current evaluation context

Color helpers return marker-wrapped text like
``__COLOR(red)text__COLOR_END__``; markers are converted to real ANSI codes
later by ``VariableSubstitutor._apply_color_filters()``.

═══════════════════════════════════════════════════════════════════════════════
OBJECT INTROSPECTION (debug)
═══════════════════════════════════════════════════════════════════════════════

``debug()`` and ``|debug`` rely on ``_inspect_object()``.
Key behavior:
- default ``max_depth=1`` (top-level fields only)
- cycle detection via ``visited`` object ids (marked as ``<cycle detected>``)
- ``@sensitive`` masking for decorated properties
- pydantic class-level attributes are filtered through
  ``_PYDANTIC_CLASS_ATTRS`` for Pydantic v2.11+ compatibility
"""

import re
from typing import Any

from pydantic import BaseModel
from simpleeval import EvalWithCompoundTypes, NameNotDefined

from action_machine.exceptions import LogTemplateError
from action_machine.logging.masking import mask_value

# Regex for finding {iif(...)} in templates.
# Important: intentionally does NOT support nested template-level iif.
_IIF_PATTERN: re.Pattern[str] = re.compile(r"\{iif\((.+?)\)\}")

# pydantic BaseModel class-level attributes that should not be accessed
# through instances (DeprecationWarning in Pydantic v2.11+).
_PYDANTIC_CLASS_ATTRS: frozenset[str] = frozenset({
    "model_fields",
    "model_computed_fields",
    "model_config",
    "model_extra",
    "model_fields_set",
    "model_json_schema",
    "model_parametrized_name",
    "model_post_init",
    "model_rebuild",
    "model_validate",
    "model_validate_json",
    "model_validate_strings",
    "model_construct",
    "model_copy",
    "model_dump",
    "model_dump_json",
})


def _color_marker(color: str, text: Any) -> str:
    """Return text wrapped in a color marker token."""
    return f"__COLOR({color}){text}__COLOR_END__"


# ----------------------------------------------------------------------
# Introspection helpers for debug()
# ----------------------------------------------------------------------


def _is_pydantic_class_attr(obj: Any, name: str) -> bool:
    """
    Check whether a name is a pydantic class-level attribute.

    Accessing these via an instance causes deprecation warnings in
    Pydantic v2.11+.
    """
    if isinstance(obj, BaseModel) and name in _PYDANTIC_CLASS_ATTRS:
        return True
    return False


def _is_public_data_attribute(obj: Any, name: str) -> bool:
    """
    Return True when name points to a public non-callable data attribute.
    """
    if name.startswith('_'):
        return False
    if _is_pydantic_class_attr(obj, name):
        return False
    try:
        attr = getattr(obj, name)
        if callable(attr):
            return False
    except Exception:
        return False
    return True


def _is_public_property(obj: Any, name: str) -> bool:
    """
    Return True when name resolves to a public property descriptor.
    """
    if name.startswith('_'):
        return False
    if _is_pydantic_class_attr(obj, name):
        return False
    for base in type(obj).__mro__:
        if name in base.__dict__:
            member = base.__dict__[name]
            if isinstance(member, property):
                return True
    return False


def _get_sensitive_config(obj: Any, name: str) -> dict[str, Any] | None:
    """
    Return @sensitive config if property getter is decorated.
    """
    for base in type(obj).__mro__:
        if name in base.__dict__:
            member = base.__dict__[name]
            if isinstance(member, property) and member.fget and hasattr(member.fget, "_sensitive_config"):
                return member.fget._sensitive_config  # type: ignore[no-any-return]
    return None


def _format_value(value: Any) -> str:
    """Return safe string representation using repr fallback."""
    try:
        return repr(value)
    except Exception:
        return "<unprintable>"


def _inspect_collection(obj: Any, indent_str: str, type_name: str) -> str:
    """Inspect list/tuple/set with compact preview."""
    if len(obj) == 0:
        return f"{indent_str}{type_name}[]"
    preview = _format_value(list(obj)[:3])
    if len(obj) > 3:
        preview = preview[:-1] + ", ...]"
    return f"{indent_str}{type_name}{preview}"


def _inspect_dict(obj: dict[str, Any], indent_str: str, type_name: str) -> str:
    """Inspect dict with bounded key/value preview."""
    if len(obj) == 0:
        return f"{indent_str}{type_name}{{}}"
    lines = [f"{indent_str}{type_name}:"]
    for k, v in list(obj.items())[:10]:
        lines.append(f"{indent_str}  {_format_value(k)}: {_format_value(v)}")
    if len(obj) > 10:
        lines.append(f"{indent_str}  ... and {len(obj)-10} more")
    return "\n".join(lines)


def _is_custom_object(value: Any) -> bool:
    """Return True for non-primitive, non-collection objects."""
    return isinstance(value, object) and not isinstance(
        value, (str, int, float, bool, type(None), list, tuple, dict, set)
    )


def _format_field_line(
    obj: Any, name: str, value: Any, indent_str: str,
    visited: set[int], max_depth: int, indent: int,
) -> str:
    """
    Format one field line for debug output.

    Cycle detection runs before max-depth checks, so direct cycles are visible
    even with ``max_depth=1``.
    """
    # Cycle check before max_depth is a key invariant.
    if _is_custom_object(value) and id(value) in visited:
        return f"{indent_str}  {name}: <cycle detected>"

    config = _get_sensitive_config(obj, name)

    if config and config.get('enabled', True):
        masked = mask_value(value, config)
        type_str = type(value).__name__
        suffix = (
            f" (sensitive: enabled, max_chars={config.get('max_chars', 3)}, "
            f"char='{config.get('char', '*')}', "
            f"max_percent={config.get('max_percent', 50)})"
        )
        value_str = masked
    elif config and not config.get('enabled', True):
        type_str = type(value).__name__
        suffix = " (sensitive: disabled)"
        value_str = _format_value(value)
    else:
        type_str = type(value).__name__
        suffix = ""
        value_str = _format_value(value)

    if max_depth > 1 and _is_custom_object(value):
        inner = _inspect_object(value, indent + 2, visited, max_depth - 1)
        return f"{indent_str}  {name}: {type_str}{suffix}\n{inner}"
    return f"{indent_str}  {name}: {type_str}{suffix} = {value_str}"


def _inspect_custom(
    obj: Any, indent_str: str, type_name: str,
    visited: set[int], max_depth: int, indent: int,
) -> str:
    """Inspect a custom object (non-builtin collection)."""
    data_attrs = {}
    for name in dir(obj):
        if _is_public_data_attribute(obj, name):
            try:
                data_attrs[name] = getattr(obj, name)
            except Exception:
                continue

    props = {}
    for name in dir(obj):
        if _is_public_property(obj, name):
            try:
                props[name] = getattr(obj, name)
            except Exception:
                continue

    # Extract extra fields from Pydantic models with extra="allow".
    if hasattr(obj, "__pydantic_extra__") and isinstance(obj.__pydantic_extra__, dict):
        for key, value in obj.__pydantic_extra__.items():
            if key.startswith('_'):
                continue
            if key in data_attrs or key in props:
                continue  # regular attribute has priority
            data_attrs[key] = value

    all_fields = {**data_attrs, **props}

    if not all_fields:
        return f"{indent_str}{type_name}: (no public fields)"

    lines = [f"{indent_str}{type_name}:"]
    for name, value in all_fields.items():
        lines.append(
            _format_field_line(obj, name, value, indent_str, visited, max_depth, indent)
        )

    return "\n".join(lines)


def _inspect_object(
    obj: Any, indent: int = 0,
    visited: set[int] | None = None, max_depth: int = 1,
) -> str:
    """Recursively build a formatted view of public object fields."""
    if visited is None:
        visited = set()

    obj_id = id(obj)
    if obj_id in visited:
        return f"{' ' * indent}<cycle detected>"
    visited.add(obj_id)

    indent_str = " " * indent
    type_name = type(obj).__name__

    # Primitive types
    if isinstance(obj, (str, int, float, bool, type(None))):
        return f"{indent_str}{type_name} = {_format_value(obj)}"

    # Collections
    if isinstance(obj, (list, tuple, set)):
        return _inspect_collection(obj, indent_str, type_name)
    if isinstance(obj, dict):
        return _inspect_dict(obj, indent_str, type_name)

    # Custom objects
    return _inspect_custom(obj, indent_str, type_name, visited, max_depth, indent)


def debug_value(obj: Any) -> str:
    """Return one-level formatted object snapshot for debug output."""
    return _inspect_object(obj, max_depth=1)


# ----------------------------------------------------------------------
# Safe functions for expression evaluator (base set, without exists).
# ----------------------------------------------------------------------

_BASE_SAFE_FUNCTIONS: dict[str, Any] = {
    "len": len,
    "upper": lambda s: str(s).upper(),
    "lower": lambda s: str(s).lower(),
    "str": str,
    "int": int,
    "float": float,
    "abs": abs,
    "format_number": lambda n, decimals=2: f"{float(n):,.{int(decimals)}f}",
    "red": lambda text: _color_marker("red", text),
    "green": lambda text: _color_marker("green", text),
    "yellow": lambda text: _color_marker("yellow", text),
    "blue": lambda text: _color_marker("blue", text),
    "magenta": lambda text: _color_marker("magenta", text),
    "cyan": lambda text: _color_marker("cyan", text),
    "white": lambda text: _color_marker("white", text),
    "grey": lambda text: _color_marker("grey", text),
    "debug": lambda obj: _inspect_object(obj, max_depth=1),
}


class _IifArgSplitter:
    """
    Split iif arguments by ';' while respecting parentheses and string literals.

    A plain ``split(';')`` is insufficient because nested expressions and
    quoted strings may contain ';'.
    """

    def __init__(self, raw: str) -> None:
        """Initialize splitter with raw argument string."""
        self._raw = raw
        self._parts: list[str] = []
        self._current: list[str] = []
        self._depth: int = 0
        self._in_string: bool = False
        self._string_char: str = ""

    def _handle_string_char(self, char: str) -> bool:
        """Handle a char when parser is currently inside a string literal."""
        if not self._in_string:
            return False
        self._current.append(char)
        if char == self._string_char:
            self._in_string = False
        return True

    def _handle_quote(self, char: str) -> bool:
        """Handle opening single/double quote when not inside string."""
        if char not in ("'", '"'):
            return False
        self._in_string = True
        self._string_char = char
        self._current.append(char)
        return True

    def _handle_structural_char(self, char: str) -> None:
        """Handle structural chars: parentheses and top-level ';' delimiter."""
        if char == "(":
            self._depth += 1
            self._current.append(char)
        elif char == ")":
            self._depth -= 1
            self._current.append(char)
        elif char == ";" and self._depth == 0:
            self._parts.append("".join(self._current))
            self._current = []
        else:
            self._current.append(char)

    def split(self) -> list[str]:
        """Split raw iif args and return parts list."""
        for char in self._raw:
            if self._handle_string_char(char):
                continue
            if self._handle_quote(char):
                continue
            self._handle_structural_char(char)

        if self._current:
            self._parts.append("".join(self._current))

        return self._parts


class ExpressionEvaluator:
    """
    Safe expression evaluator for logging templates.

    Provides safe helpers, iif evaluation, and template-level iif replacement.
    Invalid expressions raise ``LogTemplateError`` immediately.
    """

    def evaluate(self, expression: str, names: dict[str, Any]) -> Any:
        """Evaluate one expression against the provided names context."""
        def exists(name: str) -> bool:
            """Check whether variable name exists in current context."""
            return name in names

        functions = dict(_BASE_SAFE_FUNCTIONS)
        functions["exists"] = exists

        evaluator = EvalWithCompoundTypes(
            names=names,
            functions=functions,
        )
        try:
            return evaluator.eval(expression)
        except NameNotDefined as e:
            raise LogTemplateError(
                f"Variable '{e.name}' not found in expression '{expression}'"
            ) from e
        except Exception as e:
            raise LogTemplateError(
                f"Error evaluating expression '{expression}': {e}"
            ) from e

    def evaluate_iif(
        self,
        raw_args: str,
        names: dict[str, Any],
    ) -> str:
        """Evaluate ``iif(condition; true_branch; false_branch)`` expression."""
        processed_args = self.process_template(raw_args, names)
        parts = self._split_iif_args(processed_args)

        if len(parts) != 3:
            raise LogTemplateError(
                f"iif expects 3 arguments separated by ';', got {len(parts)}. "
                f"Expression: iif({raw_args})"
            )

        condition_str = parts[0].strip()
        true_expr = parts[1].strip()
        false_expr = parts[2].strip()

        condition_result = self.evaluate(condition_str, names)
        chosen_expr = true_expr if condition_result else false_expr

        stripped = chosen_expr.strip()
        if stripped.startswith("iif(") and stripped.endswith(")"):
            inner_args = stripped[4:-1]
            return self.evaluate_iif(inner_args, names)

        result = self.evaluate(chosen_expr, names)
        return str(result)

    def process_template(
        self,
        template: str,
        names: dict[str, Any],
    ) -> str:
        """Replace all ``{iif(...)} `` occurrences in template string."""
        def replacer(match: re.Match[str]) -> str:
            raw_args = match.group(1)
            return self.evaluate_iif(raw_args, names)

        return _IIF_PATTERN.sub(replacer, template)

    def _split_iif_args(self, raw: str) -> list[str]:
        """Split iif argument string via ``_IifArgSplitter``."""
        return _IifArgSplitter(raw).split()
