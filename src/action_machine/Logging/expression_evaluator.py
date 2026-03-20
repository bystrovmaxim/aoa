# ActionMachine/Logging/expression_evaluator.py
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
- String literals, numbers, bool (True/False)

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

from simpleeval import EvalWithCompoundTypes

from action_machine.Core.Exceptions import LogTemplateError

# Regular expression for finding {iif(...)} in the template.
# Uses non‑greedy capture with subsequent bracket balance check.
_IIF_PATTERN: re.Pattern[str] = re.compile(r"\{iif\((.+?)\)\}")


def _color_marker(color: str, text: Any) -> str:
    """Returns a string wrapped in a color marker."""
    return f"__COLOR({color}){text}__COLOR_END__"


# Set of safe functions available inside expressions.
# Each function has an explicit signature and performs no I/O.
_SAFE_FUNCTIONS: dict[str, Any] = {
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
    - A set of safe functions (len, upper, lower, format_number, color functions).
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
        evaluator = EvalWithCompoundTypes(
            names=names,
            functions=_SAFE_FUNCTIONS,
        )
        try:
            return evaluator.eval(expression)
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