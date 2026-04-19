# src/action_machine/logging/variable_substitutor.py
"""
Template engine for ``{%namespace.path}`` and ``{iif(...)}`` in log lines.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``VariableSubstitutor`` resolves placeholders from five namespaces, runs a
second pass for ``iif`` via ``ExpressionEvaluator``, applies color markers, and
honors ``@sensitive`` masking. ``LogCoordinator`` delegates substitution here.

Namespaces:

- **var** — message field dict. User kwargs plus system keys set by
  ``ScopedLogger``. ``level`` / ``channels`` are ``LogLevelPayload`` /
  ``LogChannelPayload`` (``mask`` + ``name`` / ``names``). Use
  ``{%var.level.name}``, ``{%var.channels.names}`` for display; ``.mask`` for raw
  flags if needed. For domain text use ``{%var.domain_name}``; ``{%var.domain}``
  stringifies the domain **type** (typically not user-facing).
- **state** — pipeline ``BaseState`` (``BaseSchema``).
- **scope** — ``LogScope`` (dict-like, not Pydantic).
- **context** — execution ``Context`` (``BaseSchema``).
- **params** — action ``BaseParams`` (``BaseSchema``).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Unknown variable, unknown namespace, bad ``iif``, underscore-leading path
  segment, or unknown color → ``LogTemplateError``.
- Inside ``{iif(...)}``, substituted values are formatted as literals for
  ``simpleeval`` (quoted strings, plain numbers/bools).
- Color: ``{%var.x|red}`` outside ``iif``; color helpers inside ``iif`` become
  markers, then ANSI in an inside-out pass for nesting.
- ``|debug`` renders a structured introspection of public fields/properties.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

1. ``_resolve_variable_raw`` / ``DotPathNavigator.navigate_with_source`` —
   resolve path; yield ``source`` + last segment for ``@sensitive`` detection.
2. ``_resolve_and_mask`` — underscore guard, sentinel check, masking.
3. ``_resolve_variable`` vs ``_format_variable_for_template`` — final string vs
   literal formatting for ``iif``.

Private attribute guard applies to **every** path segment (not only the leaf),
e.g. ``{%context._internal.public}`` and ``{%context.user._secret}`` are rejected.
Trusted code may still use ``BaseSchema.resolve`` without this restriction.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

``{%var.amount|red}``, ``{iif({%var.ok}, green('yes'), red('no'))}``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Template mistakes are treated as developer bugs and fail fast on first use.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Sole substitution + iif + color pipeline for LogCoordinator.
CONTRACT: substitute(message, var, scope, ctx, state, params) -> final str.
INVARIANTS: strict LogTemplateError policy; private segment ban; sensitive mask.
FLOW: replace {%...} → process iif → expand color markers.
FAILURES: LogTemplateError on resolution/template issues.
EXTENSION POINTS: new namespaces need resolver registration in __init__.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

import re
from collections.abc import Callable
from typing import Any

from action_machine.context.context import Context
from action_machine.logging.expression_evaluator import ExpressionEvaluator, debug_value
from action_machine.logging.log_scope import LogScope
from action_machine.logging.masking import mask_value
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from action_machine.model.exceptions import LogTemplateError
from action_machine.runtime.navigation import _SENTINEL, DotPathNavigator

# ---------------------------------------------------------------------------
# Regular expressions
# ---------------------------------------------------------------------------

# Format: {%namespace} or {%namespace.dotpath} with optional |color or |debug.
_VARIABLE_PATTERN: re.Pattern[str] = re.compile(
    r"\{%([a-zA-Z_][a-zA-Z0-9_]*)\.?([a-zA-Z_][a-zA-Z0-9_.]*)?(?:\|([a-zA-Z_]+))?\}"
)

# Used to detect iif blocks so values inside can be formatted as literals.
_IIF_BLOCK_PATTERN: re.Pattern[str] = re.compile(r"\{iif\(.*?\)\}")

# ---------------------------------------------------------------------------
# ANSI color maps for foreground/background (8 base + bright variants)
# ---------------------------------------------------------------------------

_FG_COLORS: dict[str, str] = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "grey": "90",
    "orange": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

_BG_COLORS: dict[str, str] = {
    "black": "40",
    "red": "41",
    "green": "42",
    "yellow": "43",
    "blue": "44",
    "magenta": "45",
    "cyan": "46",
    "white": "47",
    "grey": "100",
    "orange": "101",
    "bright_green": "102",
    "bright_yellow": "103",
    "bright_blue": "104",
    "bright_magenta": "105",
    "bright_cyan": "106",
    "bright_white": "107",
}

_RESET_CODE: str = "\033[0m"

# Pattern for color marker processing. Captures only markers without nested
# __COLOR( in content, which enables inside-out processing in loop passes.
_COLOR_MARKER_PATTERN: re.Pattern[str] = re.compile(
    r"__COLOR\(([a-zA-Z_]+)\)((?:(?!__COLOR\().)*)__COLOR_END__",
    re.DOTALL,
)

class VariableSubstitutor:
    """
    Resolves ``{%...}``, evaluates ``{iif}``, applies colors and ``@sensitive``.

    Dispatch table maps namespace names to resolver methods; navigation uses
    ``DotPathNavigator``. Shared resolution and masking live in
    ``_resolve_and_mask``.

    AI-CORE-BEGIN
    ROLE: Template substitution engine used by LogCoordinator.
    CONTRACT: Resolve namespaces, evaluate iif, apply masking and color markers.
    INVARIANTS: Strict fail-fast semantics via LogTemplateError.
    AI-CORE-END
    """

    def __init__(self) -> None:
        """Create evaluator and per-namespace resolver map."""
        self._evaluator: ExpressionEvaluator = ExpressionEvaluator()
        self._namespace_resolvers: dict[
            str,
            Callable[
                [str, dict[str, Any], LogScope, Context, BaseState, BaseParams],
                tuple[object, object | None, str | None],
            ],
        ] = {
            "var": self._resolve_ns_var,
            "state": self._resolve_ns_state,
            "scope": self._resolve_ns_scope,
            "context": self._resolve_ns_context,
            "params": self._resolve_ns_params,
        }

    # ----------------------------------------------------------------
    # Dot-path safety checks
    # ----------------------------------------------------------------

    @staticmethod
    def _validate_path_segments(namespace: str, path: str) -> None:
        """
        Ensure no dot-path segment starts with underscore.

        Every segment is validated (not only the leaf) to prevent bypass via
        intermediate private names:

            {%context._internal.public_key}  -> blocked on '_internal'
            {%context.__dict__.keys}         -> blocked on '__dict__'
            {%context.user._secret}          -> blocked on '_secret'
        """
        for segment in path.split("."):
            if segment.startswith("_"):
                raise LogTemplateError(
                    f"Access to name starting with underscore is forbidden: "
                    f"'{segment}' in variable {{%{namespace}.{path}}}. "
                    f"Use a public property if output is needed."
                )

    # ----------------------------------------------------------------
    # Navigation through nested objects
    # ----------------------------------------------------------------

    @staticmethod
    def _resolve_path(
        start: object,
        path: str,
    ) -> tuple[object, object | None, str | None]:
        """
        Resolve dot-path from a starting object.

        Delegates to DotPathNavigator and returns ``(value, source, last)``,
        where ``source`` is the penultimate object used for @sensitive lookup.
        """
        if not path:
            return start, None, None
        return DotPathNavigator.navigate_with_source(start, path)

    # ----------------------------------------------------------------
    # Namespace resolvers
    # ----------------------------------------------------------------

    def _resolve_ns_var(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Resolve variable from var mapping."""
        return self._resolve_path(var, path)

    def _resolve_ns_state(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Resolve variable from BaseState."""
        return self._resolve_path(state, path)

    def _resolve_ns_scope(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Resolve variable from LogScope."""
        return self._resolve_path(scope, path)

    def _resolve_ns_context(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Resolve variable from Context."""
        return self._resolve_path(ctx, path)

    def _resolve_ns_params(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Resolve variable from BaseParams."""
        return self._resolve_path(params, path)

    # ----------------------------------------------------------------
    # Detection and masking of @sensitive properties
    # ----------------------------------------------------------------

    def _get_property_config(self, obj: object, attr_name: str) -> dict[str, Any] | None:
        """
        Return @sensitive config for property if present on object MRO.
        """
        if obj is None:
            return None
        cls = type(obj)
        for base in cls.__mro__:
            if attr_name in base.__dict__:
                prop = base.__dict__[attr_name]
                if isinstance(prop, property):
                    fget = prop.fget
                    if fget is not None and hasattr(fget, "_sensitive_config"):
                        return fget._sensitive_config  # type: ignore[no-any-return]
        return None

    # ----------------------------------------------------------------
    # Variable resolution (raw value, no string conversion)
    # ----------------------------------------------------------------

    def _resolve_variable_raw(
        self,
        namespace: str,
        path: str | None,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """
        Resolve one template variable into raw value/source/last segment.
        """
        resolver = self._namespace_resolvers.get(namespace)
        if resolver is None:
            raise LogTemplateError(
                f"Unknown namespace '{namespace}' in template. "
                f"Allowed: {', '.join(sorted(self._namespace_resolvers))}. "
                f"Check variable {{%{namespace}.{path or ''}}}."
            )
        return resolver(path or "", var, scope, ctx, state, params)

    # ----------------------------------------------------------------
    # Shared resolution, validation, and masking logic
    # ----------------------------------------------------------------

    def _resolve_and_mask(
        self,
        namespace: str,
        path: str | None,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, str, dict[str, Any] | None]:
        """
        Single resolution point with safety checks and optional masking.

        Returns ``(raw_value, masked_str, config)`` for downstream formatting.
        """
        if path is not None:
            self._validate_path_segments(namespace, path)

        raw_value, source, last_segment = self._resolve_variable_raw(
            namespace, path, var, scope, ctx, state, params
        )

        if raw_value is _SENTINEL:
            raise LogTemplateError(
                f"Variable '{{%{namespace}.{path or ''}}}' not found. "
                f"Check the template and ensure the value exists in source '{namespace}'."
            )

        config = None
        if source is not None and last_segment is not None:
            config = self._get_property_config(source, last_segment)

        if config and config.get('enabled', True):
            masked_str = mask_value(raw_value, config)
        else:
            masked_str = str(raw_value)

        return raw_value, masked_str, config

    # ----------------------------------------------------------------
    # String resolution (thin wrapper over _resolve_and_mask)
    # ----------------------------------------------------------------

    def _resolve_variable(
        self,
        namespace: str,
        path: str | None,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Resolve one variable and return its final string representation.
        """
        _, masked_str, _ = self._resolve_and_mask(
            namespace, path, var, scope, ctx, state, params
        )
        return masked_str

    # ----------------------------------------------------------------
    # Formatting values as literals for iif
    # ----------------------------------------------------------------

    @staticmethod
    def _quote_if_string(raw_value: object) -> str:
        """
        Format value as simpleeval literal.

        Numbers/bools stay unquoted; strings are single-quoted; color markers
        stay unquoted to preserve later marker expansion.
        """
        if isinstance(raw_value, bool):
            return str(raw_value)
        if isinstance(raw_value, (int, float)):
            return str(raw_value)
        s = str(raw_value)
        if "__COLOR(" in s and "__COLOR_END__" in s:
            return s
        s = s.replace("'", "\\'")
        return f"'{s}'"

    # ----------------------------------------------------------------
    # Variable substitution helpers
    # ----------------------------------------------------------------

    def _substitute_simple(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Fast path when no iif is present: replace {%...} directly.
        """
        def replacer(match: re.Match[str]) -> str:
            namespace = match.group(1)
            path = match.group(2)
            filter_name = match.group(3)

            if filter_name == "debug":
                raw_value, _, _ = self._resolve_and_mask(
                    namespace, path, var, scope, ctx, state, params
                )
                return debug_value(raw_value)

            _, masked_str, _ = self._resolve_and_mask(
                namespace, path, var, scope, ctx, state, params
            )

            if filter_name:
                return f"__COLOR({filter_name}){masked_str}__COLOR_END__"

            return masked_str

        return _VARIABLE_PATTERN.sub(replacer, message)

    def _format_variable_for_template(
        self,
        match: re.Match[str],
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        inside_iif: bool,
    ) -> str:
        """
        Format one variable occurrence with iif/literal/filter awareness.
        """
        namespace = match.group(1)
        path = match.group(2)
        filter_name = match.group(3)

        raw_value, masked_str, _ = self._resolve_and_mask(
            namespace, path, var, scope, ctx, state, params
        )

        if inside_iif:
            if isinstance(raw_value, (bool, int, float)):
                formatted = masked_str
            else:
                formatted = self._quote_if_string(masked_str)
        else:
            formatted = masked_str

        if filter_name == "debug":
            return debug_value(raw_value)

        if filter_name:
            return f"__COLOR({filter_name}){formatted}__COLOR_END__"

        return formatted

    def _substitute_with_iif_detection(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Slow path with iif detection: format variables by block position.
        """
        iif_ranges = [
            (m.start(), m.end())
            for m in _IIF_BLOCK_PATTERN.finditer(message)
        ]

        def _inside_iif(pos: int) -> bool:
            return any(start <= pos < end for start, end in iif_ranges)

        def replacer(match: re.Match[str]) -> str:
            inside = _inside_iif(match.start())
            return self._format_variable_for_template(
                match, var, scope, ctx, state, params, inside
            )

        return _VARIABLE_PATTERN.sub(replacer, message)

    def _substitute_variables(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        has_iif: bool,
    ) -> str:
        """
        First-pass dispatcher choosing fast/slow substitution strategy.
        """
        if has_iif:
            return self._substitute_with_iif_detection(
                message, var, scope, ctx, state, params
            )
        return self._substitute_simple(message, var, scope, ctx, state, params)

    # ----------------------------------------------------------------
    # Post-processing color markers -> ANSI codes
    # ----------------------------------------------------------------

    def _resolve_color_name(self, color_name: str) -> str:
        """
        Convert symbolic color name into ANSI escape sequence.

        Supported formats:
        - ``bg_<color>`` background only
        - ``<fg>_on_<bg>`` foreground + background
        - ``<color>`` foreground only
        """
        if color_name.startswith("bg_"):
            bg_name = color_name[3:]
            bg_code = _BG_COLORS.get(bg_name)
            if bg_code is None:
                raise LogTemplateError(f"Unknown background color: '{bg_name}'")
            return f"\033[{bg_code}m"

        if "_on_" in color_name:
            parts = color_name.split("_on_", 1)
            if len(parts) != 2:
                raise LogTemplateError(
                    f"Invalid color format: '{color_name}'. "
                    f"Use 'foreground_on_background'."
                )
            fg_name, bg_name = parts
            fg_code = _FG_COLORS.get(fg_name)
            bg_code = _BG_COLORS.get(bg_name)
            if fg_code is None:
                raise LogTemplateError(f"Unknown foreground color: '{fg_name}'")
            if bg_code is None:
                raise LogTemplateError(f"Unknown background color: '{bg_name}'")
            return f"\033[{fg_code};{bg_code}m"

        fg_code = _FG_COLORS.get(color_name)
        if fg_code is None:
            raise LogTemplateError(f"Unknown color: '{color_name}'")
        return f"\033[{fg_code}m"

    def _apply_color_filters(self, text: str) -> str:
        """
        Replace color markers with ANSI codes using inside-out passes.
        """
        while _COLOR_MARKER_PATTERN.search(text):
            def replacer(match: re.Match[str]) -> str:
                color_name = match.group(1)
                content = match.group(2)
                ansi_code = self._resolve_color_name(color_name)
                return f"{ansi_code}{content}{_RESET_CODE}"

            text = _COLOR_MARKER_PATTERN.sub(replacer, text)

        return text

    # ----------------------------------------------------------------
    # Public method
    # ----------------------------------------------------------------

    def substitute(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Run ``{%...}`` replacement, then ``{iif}``, then expand color markers.

        Args:
            message: Template string.
            var: Per-message dict (user keys + ``level``, ``channels``,
                ``domain``, ``domain_name`` from the logging system).
            scope: Current ``LogScope``.
            ctx: Execution context.
            state: Pipeline state.
            params: Action parameters.

        Returns:
            Fully resolved text, possibly with ANSI codes.

        Raises:
            LogTemplateError: missing key, bad namespace, bad ``iif``, private
                path segment, or unknown color.
        """
        has_iif = "{iif(" in message

        # Pass 1: substitute {%...}, keep color markers.
        resolved = self._substitute_variables(
            message, var, scope, ctx, state, params, has_iif
        )

        # Pass 2: evaluate {iif(...)}.
        if has_iif:
            resolved = self._evaluator.process_template(resolved, {})

        # Pass 3: expand color markers to ANSI (inside-out).
        return self._apply_color_filters(resolved)
