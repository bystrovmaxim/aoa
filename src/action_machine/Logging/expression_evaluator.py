# src/action_machine/Logging/expression_evaluator.py
"""
Expression evaluator for AOA logging templates.

Uses the simpleeval library for safe evaluation of expressions inside
the {iif(condition; true_value; false_value)} construct.

simpleeval does not support import, exec, eval, __builtins__,
or any access to the file system or network. This guarantees that
the logger template cannot execute arbitrary code.

The evaluator provides:
- Comparison operators: ==, !=, >, <, >=, <=
- Logical operators: and, or, not
- Arithmetic: +, -, *, /
- Built-in functions: len, upper, lower, format_number
- Color functions: red, green, yellow, blue, magenta, cyan, white, grey
- Debug function: debug(obj) – returns a formatted string with public fields/properties
  of the object (useful for introspection in log templates).
  **Note:** As of version 0.0.6, debug shows only the immediate fields of the object
  (max_depth=1) to prevent log flooding. For deeper inspection, call debug on the
  nested attribute directly.
- Exists function: exists(name) – returns True if a variable with the given name exists
  in the current evaluation context, False otherwise. Useful for conditional logging
  when a variable may be missing.

All variables from the execution context (var, state, params, context, scope)
are available inside expressions as literal values, substituted by the
coordinator BEFORE iif evaluation.

Color functions return a string wrapped in a marker like `__COLOR(red)text__COLOR_END__`,
which is later replaced with actual ANSI codes by VariableSubstitutor.

No error suppression. If an expression is invalid, LogTemplateError is raised.
An error in a log template is a developer bug and must be detected immediately
on the first run.

Parsing of iif arguments is handled by a separate class _IifArgSplitter,
which correctly handles nested parentheses and string literals.
"""

import re
from typing import Any

from simpleeval import EvalWithCompoundTypes, NameNotDefined

from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.masking import mask_value

# Regular expression for finding {iif(...)} in the template.
# Uses non‑greedy capture with subsequent bracket balance check.
_IIF_PATTERN: re.Pattern[str] = re.compile(r"\{iif\((.+?)\)\}")


def _color_marker(color: str, text: Any) -> str:
    """Returns a string wrapped in a color marker."""
    return f"__COLOR({color}){text}__COLOR_END__"


# ----------------------------------------------------------------------
# Debug introspection helpers
# ----------------------------------------------------------------------

def _is_public_data_attribute(obj: Any, name: str) -> bool:
    """
    Determines if a name should be considered a public data attribute.
    Excludes:
    - names starting with underscore
    - methods (callable)
    """
    if name.startswith('_'):
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
    Checks if name is a public property (excluding underscore names).
    """
    if name.startswith('_'):
        return False
    for base in type(obj).__mro__:
        if name in base.__dict__:
            member = base.__dict__[name]
            if isinstance(member, property):
                return True
    return False


def _get_sensitive_config(obj: Any, name: str) -> dict[str, Any] | None:
    """
    Returns sensitive config if the property has @sensitive decorator.
    """
    for base in type(obj).__mro__:
        if name in base.__dict__:
            member = base.__dict__[name]
            if isinstance(member, property) and member.fget and hasattr(member.fget, "_sensitive_config"):
                config = member.fget._sensitive_config
                # mypy compatibility
                return config  # type: ignore[no-any-return]
    return None


def _format_value(value: Any) -> str:
    """
    Return a safe string representation of a value, with no truncation.
    """
    try:
        return repr(value)
    except Exception:
        return "<unprintable>"


def _inspect_collection(obj: Any, indent_str: str, type_name: str) -> str:
    """Inspect a list, tuple or set."""
    if len(obj) == 0:
        return f"{indent_str}{type_name}[]"
    preview = _format_value(list(obj)[:3])
    if len(obj) > 3:
        preview = preview[:-1] + ", ...]"
    return f"{indent_str}{type_name}{preview}"


def _inspect_dict(obj: dict[str, Any], indent_str: str, type_name: str) -> str:
    """Inspect a dictionary."""
    if len(obj) == 0:
        return f"{indent_str}{type_name}{{}}"
    lines = [f"{indent_str}{type_name}:"]
    for k, v in list(obj.items())[:10]:
        lines.append(f"{indent_str}  {_format_value(k)}: {_format_value(v)}")
    if len(obj) > 10:
        lines.append(f"{indent_str}  ... and {len(obj)-10} more")
    return "\n".join(lines)


def _format_field_line(
    obj: Any, name: str, value: Any, indent_str: str, visited: set[int], max_depth: int, indent: int
) -> str:
    """
    Format a single field line for debug output.

    Returns either a single line (if recursion depth exhausted or value is primitive)
    or a line plus a recursively inspected block.
    """
    config = _get_sensitive_config(obj, name)

    is_custom_object = isinstance(value, object) and not isinstance(
        value, (str, int, float, bool, type(None), list, tuple, dict, set)
    )

    if config and config.get('enabled', True):
        masked = mask_value(value, config)
        type_str = type(value).__name__
        suffix = f" (sensitive: enabled, max_chars={config.get('max_chars', 3)}, char='{config.get('char', '*')}', max_percent={config.get('max_percent', 50)})"
        value_str = masked
    elif config and not config.get('enabled', True):
        type_str = type(value).__name__
        suffix = " (sensitive: disabled)"
        value_str = _format_value(value)
    else:
        type_str = type(value).__name__
        suffix = ""
        value_str = _format_value(value)

    if max_depth > 1 and is_custom_object:
        inner = _inspect_object(value, indent + 2, visited, max_depth - 1)
        return f"{indent_str}  {name}: {type_str}{suffix}\n{inner}"
    return f"{indent_str}  {name}: {type_str}{suffix} = {value_str}"


def _inspect_custom(
    obj: Any, indent_str: str, type_name: str, visited: set[int], max_depth: int, indent: int
) -> str:
    """Inspect a custom object (not a built-in collection)."""
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

    all_fields = {**data_attrs, **props}

    if not all_fields:
        return f"{indent_str}{type_name}: (no public fields)"

    lines = [f"{indent_str}{type_name}:"]
    for name, value in all_fields.items():
        # Check for cycles
        val_id = id(value)
        if val_id in visited:
            lines.append(f"{indent_str}  {name}: <cycle detected>")
            continue

        lines.append(_format_field_line(obj, name, value, indent_str, visited, max_depth, indent))

    return "\n".join(lines)


def _inspect_object(obj: Any, indent: int = 0, visited: set[int] | None = None, max_depth: int = 1) -> str:
    """
    Recursively builds a string representation of an object's public data fields and properties.

    Args:
        obj: The object to inspect.
        indent: Current indentation level (number of spaces).
        visited: Set of object ids already processed (to avoid cycles).
        max_depth: Maximum recursion depth. Defaults to 1 (show only direct fields).
                   If max_depth > 1, nested objects are expanded recursively.

    Returns:
        Formatted multiline string.
    """
    if visited is None:
        visited = set()

    obj_id = id(obj)
    if obj_id in visited:
        return f"{' ' * indent}<cycle detected>"
    visited.add(obj_id)

    indent_str = " " * indent
    type_name = type(obj).__name__

    # Basic types
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
    """
    Return a formatted string representation of an object for debug output.

    This is a convenience wrapper around _inspect_object with max_depth=1.
    It is intended to be used as a filter in templates: {%var.user|debug}
    or as a function inside iif: debug(var.user).

    The output shows only immediate fields (no recursion) to avoid flooding
    the logs. To inspect nested objects, call debug on the nested attribute
    directly.

    Example:
        {%var.user|debug}
        or
        {iif(1==1; debug(var.user); '')}
    """
    return _inspect_object(obj, max_depth=1)


# ----------------------------------------------------------------------
# Safe functions for expression evaluator (base set, without exists)
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
    # Color functions – they wrap the argument in a marker
    "red": lambda text: _color_marker("red", text),
    "green": lambda text: _color_marker("green", text),
    "yellow": lambda text: _color_marker("yellow", text),
    "blue": lambda text: _color_marker("blue", text),
    "magenta": lambda text: _color_marker("magenta", text),
    "cyan": lambda text: _color_marker("cyan", text),
    "white": lambda text: _color_marker("white", text),
    "grey": lambda text: _color_marker("grey", text),
    # Debug function – returns a formatted string for object introspection
    # Changed default max_depth to 1 (show only direct fields)
    "debug": lambda obj: _inspect_object(obj, max_depth=1),
}


class _IifArgSplitter:
    """
    Splits iif arguments by ';' taking into account nested parentheses
    and string literals.

    A simple split(';') does not work because there may be nested iif
    or strings containing ';'.

    Principle:
    1. Iterate over characters of the input string.
    2. If inside a string literal, accumulate characters until the closing quote.
    3. If an opening quote is encountered, enter string literal mode.
    4. Otherwise, handle structural characters: parentheses change depth,
       ';' at depth 0 separates arguments.
    """

    def __init__(self, raw: str) -> None:
        """
        Initializes the parser.

        Args:
            raw: argument string without outer parentheses.
                 Example: "amount > 1000; 'HIGH'; 'LOW'".
        """
        self._raw = raw
        self._parts: list[str] = []
        self._current: list[str] = []
        self._depth: int = 0
        self._in_string: bool = False
        self._string_char: str = ""

    def _handle_string_char(self, char: str) -> bool:
        """
        Handles a character when inside a string literal.

        Inside a string literal, all characters are accumulated without
        interpretation. The only special character is the closing quote
        (matching the opening one), which ends the string mode.

        Args:
            char: current character to process.

        Returns:
            True if the character was handled (we are inside a string),
            False if we are not in string mode and the character should be
            processed by another method.
        """
        if not self._in_string:
            return False
        self._current.append(char)
        if char == self._string_char:
            self._in_string = False
        return True

    def _handle_quote(self, char: str) -> bool:
        """
        Handles an opening quote (single or double).

        If the character is a quote, enters string literal mode.
        All subsequent characters will be accumulated without interpretation
        until the closing quote.

        Args:
            char: current character to check.

        Returns:
            True if the character was a quote and handled,
            False if it is not a quote.
        """
        if char not in ("'", '"'):
            return False
        self._in_string = True
        self._string_char = char
        self._current.append(char)
        return True

    def _handle_structural_char(self, char: str) -> None:
        """
        Handles structural characters: parentheses and the separator ';'.

        Opening '(' increases nesting depth.
        Closing ')' decreases nesting depth.
        Semicolon ';' at depth 0 ends the current argument and starts a new one.
        At non‑zero depth, ';' is part of a nested expression and is simply accumulated.
        All other characters are accumulated into the current argument.

        Args:
            char: current character to process.
        """
        if char == "(":
            self._depth += 1
            self._current.append(char)
        elif char == ")":
            self._depth -= 1
            self._current.append(char)
        elif char == ";" and self._depth == 0:
            # Top‑level argument separator – finish current argument and start a new one.
            self._parts.append("".join(self._current))
            self._current = []
        else:
            self._current.append(char)

    def split(self) -> list[str]:
        """
        Splits the argument string and returns a list of parts.

        Iterates over each character of the input string, applying handlers
        in priority order:
        1. _handle_string_char – if inside a string literal.
        2. _handle_quote – if the character is an opening quote.
        3. _handle_structural_char – for parentheses, ';', and ordinary characters.

        After processing all characters, adds the last accumulated argument
        (if not empty) to the result list.

        Returns:
            List of strings – iif arguments (ideally 3 for a valid iif).
        """
        for char in self._raw:
            # Priority 1: character inside a string literal.
            if self._handle_string_char(char):
                continue
            # Priority 2: opening quote.
            if self._handle_quote(char):
                continue
            # Priority 3: structural characters (parentheses, ';', rest).
            self._handle_structural_char(char)

        # Add the last accumulated argument.
        if self._current:
            self._parts.append("".join(self._current))

        return self._parts


class ExpressionEvaluator:
    """
    Safe expression evaluator for logging templates.

    Wraps simpleeval, providing:
    - A set of safe functions (len, upper, lower, format_number, color functions, debug, exists).
    - Protection against arbitrary code execution.
    - evaluate method for single expressions.
    - evaluate_iif method for iif constructs.
    - process_template method to handle all {iif(...)} in a template string.

    Does NOT suppress exceptions. If an expression is invalid,
    LogTemplateError is raised. An error in a log template is a developer bug
    and must be detected immediately.
    """

    def evaluate(self, expression: str, names: dict[str, Any]) -> Any:
        """
        Evaluates a single expression in the context of variables.

        Args:
            expression: Python‑like expression string.
            names: dictionary of variables available in the expression.

        Returns:
            Evaluation result (any type).

        Raises:
            LogTemplateError: if the expression is invalid or contains
                undefined variables.
        """
        # Add the 'exists' function that checks if a variable name is defined in 'names'
        def exists(name: str) -> bool:
            """Check if a variable exists in the current evaluation context."""
            # The name is a string literal (e.g., 'var.amount'), not the variable itself.
            return name in names

        # Merge base functions with exists
        functions = dict(_BASE_SAFE_FUNCTIONS)
        functions["exists"] = exists

        evaluator = EvalWithCompoundTypes(
            names=names,
            functions=functions,
        )
        try:
            return evaluator.eval(expression)
        except NameNotDefined as e:
            # Provide a user‑friendly message for missing variables
            raise LogTemplateError(f"Variable '{e.name}' not found in expression '{expression}'") from e
        except Exception as e:
            raise LogTemplateError(f"Error evaluating expression '{expression}': {e}") from e

    def evaluate_iif(
        self,
        raw_args: str,
        names: dict[str, Any],
    ) -> str:
        """
        Evaluates an iif(condition; true_branch; false_branch) construct.

        Splits the argument string by ';', evaluates the condition,
        and returns the chosen branch as a string.

        Supports nested iif – if the chosen branch starts with "iif(",
        it is handled recursively via another call to evaluate_iif.
        Also, nested iif in the form {iif(...)} are processed via
        process_template before argument splitting.

        Args:
            raw_args: string like "condition; true_value; false_value".
            names: dictionary of variables for substitution.

        Returns:
            String result of the chosen branch.

        Raises:
            LogTemplateError: if:
                - the number of iif arguments is not 3.
                - error evaluating the condition.
                - error evaluating the chosen branch.
        """
        # First, process any nested iif in the form {iif(...)} inside the arguments
        processed_args = self.process_template(raw_args, names)
        parts = self._split_iif_args(processed_args)

        if len(parts) != 3:
            raise LogTemplateError(
                f"iif expects 3 arguments separated by ';', got {len(parts)}. Expression: iif({raw_args})"
            )

        condition_str = parts[0].strip()
        true_expr = parts[1].strip()
        false_expr = parts[2].strip()

        # Evaluate condition – any error will propagate as LogTemplateError.
        condition_result = self.evaluate(condition_str, names)

        chosen_expr = true_expr if condition_result else false_expr

        # Check if the chosen branch is a nested iif call without curly braces,
        # e.g., iif(amount > 100000; 'HIGH'; 'LOW')
        # If so, recursively call evaluate_iif.
        stripped = chosen_expr.strip()
        if stripped.startswith("iif(") and stripped.endswith(")"):
            # Extract inner arguments – remove "iif(" and ")"
            inner_args = stripped[4:-1]
            return self.evaluate_iif(inner_args, names)

        # The chosen branch may be a string literal or an expression.
        # Any evaluation error will be raised as LogTemplateError.
        result = self.evaluate(chosen_expr, names)
        return str(result)

    def process_template(
        self,
        template: str,
        names: dict[str, Any],
    ) -> str:
        """
        Processes all {iif(...)} occurrences in a template string.

        Finds each {iif(...)}, evaluates it via evaluate_iif,
        and substitutes the result.

        Args:
            template: template string with {iif(...)} constructs.
            names: dictionary of variables for substitution.

        Returns:
            String with all iif constructs replaced by their evaluated results.

        Raises:
            LogTemplateError: if any iif expression is invalid.
        """

        def replacer(match: re.Match[str]) -> str:
            raw_args = match.group(1)
            return self.evaluate_iif(raw_args, names)

        return _IIF_PATTERN.sub(replacer, template)

    def _split_iif_args(self, raw: str) -> list[str]:
        """
        Splits iif arguments using the dedicated _IifArgSplitter.

        Delegates all parsing logic to _IifArgSplitter, which tracks
        parentheses depth and string literals.

        Args:
            raw: argument string without outer iif parentheses.

        Returns:
            List of parts (ideally 3 for a valid iif).
        """
        return _IifArgSplitter(raw).split()