# src/action_machine/Logging/variable_substitutor.py
"""
Variable substitutor for AOA logging templates.

VariableSubstitutor is responsible for:
1. Resolving variables {%namespace.dotpath} from five sources:
   - var – developer‑supplied dictionary.
   - state – current pipeline state (BaseState).
   - scope – LogScope (location in the pipeline).
   - context – execution context (ReadableMixin).
   - params – action input parameters (ReadableMixin).
2. Two‑pass substitution:
   - Pass 1: replace {%namespace.path} with values.
     Inside {iif(...)} values are substituted as literals
     (strings in quotes, numbers as is).
   - Pass 2: evaluate {iif(...)} via ExpressionEvaluator.
3. Strict error policy:
   - Variable not found → LogTemplateError.
   - Unknown namespace → LogTemplateError.
   - Invalid iif → LogTemplateError.
   - Access to a name starting with underscore → LogTemplateError.
4. Color filters: syntax {%var.amount|red} (outside iif) and color functions
   like red('text') (inside iif) are supported. They are turned into markers
   and later replaced with ANSI codes.
5. Debug filter: syntax {%var.obj|debug} outputs a formatted representation
   of the object (public fields and properties) using the debug_value function.
   This is a convenient shortcut for the debug() function.
6. Sensitive data masking: if the resolved variable is a property decorated
   with @sensitive, its value is masked according to the decorator parameters.

The only public method is substitute(). It takes the template message
and all data sources, performs substitution, and returns the final string.
LogCoordinator calls substitute() instead of its own implementation.

Internally, a dispatch dictionary _namespace_resolvers allows easy addition
of new data sources. Each namespace is handled by a separate private resolver
that uses _resolve_one_step to navigate through the path segments and returns
a tuple (value, source_object) where source_object is the object from which
the last step was taken (used for sensitive detection).

Color markers: during substitution, if a variable name contains a pipe `|`,
the part after the pipe is treated as a color name. The resolved value is
wrapped in a marker like `__COLOR(color)value__COLOR_END__`. Color functions
called inside iif return the same markers. After all substitutions and iif
evaluation, the final string passes through `_apply_color_filters`, which
replaces markers with actual ANSI codes.

The color name can be either a simple foreground color (e.g., "red"), a background
color prefixed with "bg_" (e.g., "bg_red"), or a combination
"foreground_on_background" (e.g., "red_on_blue"). Any combination of the available
colors is supported. If an unknown color name is used, LogTemplateError is raised
immediately.
"""

import re
from collections.abc import Callable
from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.core.readable_mixin import ReadableMixin
from action_machine.logging.expression_evaluator import ExpressionEvaluator, debug_value
from action_machine.logging.log_scope import LogScope
from action_machine.logging.masking import mask_value

# ---------------------------------------------------------------------------
# Regular expressions
# ---------------------------------------------------------------------------
# Format: {%namespace} or {%namespace.dotpath} optionally followed by |color or |debug
# Group 1 (namespace): data source (var, state, scope, context, params).
# Group 2 (optional path): dot‑path inside the source (may be None).
# Group 3 (optional filter): color name or "debug".
_VARIABLE_PATTERN: re.Pattern[str] = re.compile(
    r"\{%([a-zA-Z_][a-zA-Z0-9_]*)\.?([a-zA-Z_][a-zA-Z0-9_.]*)?(?:\|([a-zA-Z_]+))?\}"
)
# Used to detect iif blocks so that inside them we substitute values as literals.
_IIF_BLOCK_PATTERN: re.Pattern[str] = re.compile(r"\{iif\(.*?\)\}")


# Sentinel to distinguish "attribute not found" from "attribute is None".
_SENTINEL: object = object()


# ANSI color codes for foreground and background (8 basic + bright variants)
_FG_COLORS: dict[str, str] = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",   # purple
    "cyan": "36",
    "white": "37",
    "grey": "90",      # bright black
    "orange": "91",    # bright red (often used as orange)
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
    "grey": "100",     # bright black background
    "orange": "101",   # bright red background
    "bright_green": "102",
    "bright_yellow": "103",
    "bright_blue": "104",
    "bright_magenta": "105",
    "bright_cyan": "106",
    "bright_white": "107",
}

_RESET_CODE: str = "\033[0m"


class VariableSubstitutor:
    """
    Variable substitutor and iif evaluator for logging templates.
    Contains all logic:
    - Resolving variables from five namespaces (var, state, scope,
      context, params) via a dispatch dictionary.
    - Traversing nested objects by dot‑path using _resolve_one_step.
    - Formatting values as literals for simpleeval
      (strings in quotes, numbers as is).
    - Two‑pass substitution: first {%...}, then {iif(...)}.
    - Strict error handling: underscores in names cause LogTemplateError.
    - Color filters via |color syntax (outside iif) and color functions
      (inside iif), turned into markers and post‑processed.
    - Debug filter via |debug syntax, outputs object introspection.
    - Sensitive data masking: if the resolved variable is a property decorated
      with @sensitive, the value is masked according to the decorator parameters.

    Attributes:
        _evaluator: ExpressionEvaluator instance for iif evaluation.
        _namespace_resolvers: dispatch dictionary namespace → resolver method.
    """

    def __init__(self) -> None:
        """Initializes the substitutor with an evaluator and resolvers."""
        self._evaluator: ExpressionEvaluator = ExpressionEvaluator()
        # Dispatch dictionary: namespace → resolver method.
        self._namespace_resolvers: dict[
            str,
            Callable[
                [str, dict[str, Any], LogScope, Context, BaseState, BaseParams],
                tuple[object, object | None],  # returns (value, source_object)
            ],
        ] = {
            "var": self._resolve_ns_var,
            "state": self._resolve_ns_state,
            "scope": self._resolve_ns_scope,
            "context": self._resolve_ns_context,
            "params": self._resolve_ns_params,
        }

    # ----------------------------------------------------------------
    # Navigation helper (similar to ReadableMixin._resolve_one_step)
    # ----------------------------------------------------------------
    @staticmethod
    def _resolve_step_readable(
        current: ReadableMixin,
        segment: str,
    ) -> object:
        """Step navigation for objects with ReadableMixin (uses __getitem__)."""
        try:
            return current[segment]
        except KeyError:
            return _SENTINEL

    @staticmethod
    def _resolve_step_dict(
        current: dict[str, object],
        segment: str,
    ) -> object:
        """Step navigation for plain dictionaries."""
        if segment in current:
            return current[segment]
        return _SENTINEL

    @staticmethod
    def _resolve_step_generic(
        current: object,
        segment: str,
    ) -> object:
        """Step navigation for any other object via getattr."""
        return getattr(current, segment, _SENTINEL)

    def _resolve_one_step(
        self,
        current: object,
        segment: str,
    ) -> object:
        """
        Performs one step of navigation, choosing strategy based on the current object's type.

        Args:
            current: current object at this step.
            segment: name of the key/attribute to move to.

        Returns:
            Found value, or _SENTINEL if the step failed.
        """
        if isinstance(current, ReadableMixin):
            return self._resolve_step_readable(current, segment)
        if isinstance(current, dict):
            return self._resolve_step_dict(current, segment)
        return self._resolve_step_generic(current, segment)

    def _resolve_path(
        self,
        start: object,
        path: str,
    ) -> tuple[object, object | None]:
        """
        Resolves a dot‑path starting from the given object, and returns the final value
        along with the source object from which the last step was taken.

        Args:
            start: starting object.
            path: dot‑separated path string.

        Returns:
            A tuple (value, source_object) where value is the value at the end of the path,
            and source_object is the object from which the last segment was taken
            (or None if the path is empty or the source cannot be determined).
            If any step fails, returns (_SENTINEL, None).
        """
        if not path:
            return start, None

        segments = path.split(".")
        current = start
        source = None

        for segment in segments:
            source = current  # the object we are about to step from
            current = self._resolve_one_step(current, segment)
            if current is _SENTINEL:
                return _SENTINEL, None
            # after the last step, source is the object that contained the final attribute
        return current, source

    # ----------------------------------------------------------------
    # Namespace resolvers (now using _resolve_path)
    # ----------------------------------------------------------------
    def _resolve_ns_var(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, object | None]:
        """Resolves a variable from the var dictionary."""
        return self._resolve_path(var, path)

    def _resolve_ns_state(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, object | None]:
        """Resolves a variable from the BaseState."""
        return self._resolve_path(state, path)

    def _resolve_ns_scope(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, object | None]:
        """Resolves a variable from the LogScope."""
        # LogScope is a Mapping, treat it like a dict
        return self._resolve_path(scope, path)

    def _resolve_ns_context(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, object | None]:
        """Resolves a variable from the Context."""
        return self._resolve_path(ctx, path)

    def _resolve_ns_params(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, object | None]:
        """Resolves a variable from the BaseParams."""
        return self._resolve_path(params, path)

    # ----------------------------------------------------------------
    # Sensitive detection and masking
    # ----------------------------------------------------------------
    def _get_property_config(self, obj: object, attr_name: str) -> dict[str, Any] | None:
        """
        Checks if the given object's class (or any superclass) has a property
        named attr_name, and if that property's getter has a _sensitive_config attribute.

        Args:
            obj: the object that is the source of the attribute.
            attr_name: the name of the attribute.

        Returns:
            The config dict if the property exists and is sensitive, otherwise None.
        """
        if obj is None:
            return None
        cls = type(obj)
        # Traverse the MRO
        for base in cls.__mro__:
            if attr_name in base.__dict__:
                prop = base.__dict__[attr_name]
                if isinstance(prop, property):
                    fget = prop.fget
                    if fget is not None and hasattr(fget, "_sensitive_config"):
                        config = fget._sensitive_config
                        # By design, config is a dict with the expected keys.
                        return config  # type: ignore[no-any-return]
        return None

    # ----------------------------------------------------------------
    # Main variable resolution (raw value, no string conversion)
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
    ) -> tuple[object, object | None]:
        """
        Resolves a single variable from the template – raw value (not str) and the source object.

        Uses the dispatch dictionary _namespace_resolvers.
        If the namespace is unknown, raises LogTemplateError.

        Args:
            namespace: first segment of the variable ("var", "context", ...).
            path: remaining dot‑path after the namespace (may be None).
            var: developer‑supplied variables.
            scope: current call scope.
            ctx: execution context.
            state: current pipeline state.
            params: action input parameters.

        Returns:
            Tuple (raw value, source_object). source_object is the object from which the last
            step was taken (may be None if not applicable).

        Raises:
            LogTemplateError: if namespace is unknown.
        """
        resolver = self._namespace_resolvers.get(namespace)
        if resolver is None:
            raise LogTemplateError(
                f"Unknown namespace '{namespace}' in template. "
                f"Allowed: {', '.join(sorted(self._namespace_resolvers))}. "
                f"Check variable {{%{namespace}.{path or ''}}}."
            )
        # If path is None, treat as empty string (returns the whole namespace object)
        return resolver(path or "", var, scope, ctx, state, params)

    # ----------------------------------------------------------------
    # String resolution with None check, underscore guard, and masking
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
        Resolves a single variable – returns its string representation, possibly masked.
        """
        # If path is None, we are accessing the whole namespace object.
        # In that case, there is no last segment to check for underscore.
        last_segment = None
        if path is not None:
            # Check for underscore in the last segment
            last_segment = path.split(".")[-1]
            if last_segment.startswith("_"):
                raise LogTemplateError(
                    f"Access to name starting with underscore is forbidden: '{last_segment}' "
                    f"in variable {{%{namespace}.{path}}}. Use a public property if output is needed."
                )

        raw_value, source = self._resolve_variable_raw(
            namespace, path, var, scope, ctx, state, params
        )
        if raw_value is _SENTINEL:
            raise LogTemplateError(
                f"Variable '{{%{namespace}.{path or ''}}}' not found. "
                f"Check the template and ensure the value exists in source '{namespace}'."
            )

        # Check if this is a sensitive property (only if we have a last segment)
        config = None
        if source is not None and last_segment is not None:
            config = self._get_property_config(source, last_segment)

        if config:
            # If masking is explicitly disabled, return the string as is.
            if not config.get('enabled', True):
                return str(raw_value)
            # Otherwise apply masking.
            return mask_value(raw_value, config)

        # Normal conversion to string
        return str(raw_value)

    # ----------------------------------------------------------------
    # Formatting values as literals for iif
    # ----------------------------------------------------------------
    @staticmethod
    def _quote_if_string(raw_value: object) -> str:
        """
        Formats a raw value as a literal for simpleeval.
        Numbers and bools are returned as is (as strings), strings are quoted.

        If the string already contains a color marker (__COLOR(...)), it is
        returned without quotes to preserve the marker for later replacement.

        Args:
            raw_value: raw value.

        Returns:
            String suitable for insertion into a simpleeval expression.
        """
        if isinstance(raw_value, bool):
            return str(raw_value)
        if isinstance(raw_value, (int, float)):
            return str(raw_value)
        s = str(raw_value)
        # If this is already a color marker, do not add quotes
        if "__COLOR(" in s and "__COLOR_END__" in s:
            return s
        s = s.replace("'", "\\'")
        return f"'{s}'"

    # ----------------------------------------------------------------
    # Variable substitution – three private methods
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
        Fast path: no iif – simple replacement of {%...} → str(value).
        Handles color filters by wrapping the result in a marker.
        Handles debug filter by outputting object introspection.
        """
        def replacer(match: re.Match[str]) -> str:
            namespace = match.group(1)
            path = match.group(2)  # may be None
            filter_name = match.group(3)  # may be None, a color, or "debug"
            value = self._resolve_variable(
                namespace, path, var, scope, ctx, state, params
            )

            if filter_name == "debug":
                # Get raw value again for debug (we have it already resolved as string, but we need the object)
                raw_value, _ = self._resolve_variable_raw(
                    namespace, path, var, scope, ctx, state, params
                )
                return debug_value(raw_value)
            if filter_name:
                # Wrap in color marker
                return f"__COLOR({filter_name}){value}__COLOR_END__"
            return value

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
        Форматирует одно вхождение переменной в шаблоне, учитывая маскировку,
        фильтры и нахождение внутри/вне iif.
        """
        namespace = match.group(1)
        path = match.group(2)
        filter_name = match.group(3)
        raw_value, source = self._resolve_variable_raw(
            namespace, path, var, scope, ctx, state, params
        )
        if raw_value is _SENTINEL:
            raise LogTemplateError(
                f"Variable '{{%{namespace}.{path or ''}}}' not found. "
                f"Check the template and ensure the value exists in source '{namespace}'."
            )

        last_segment = None
        if path is not None:
            last_segment = path.split(".")[-1]

        config = None
        if source is not None and last_segment is not None:
            config = self._get_property_config(source, last_segment)

        # Форматирование в зависимости от того, находится ли переменная внутри iif
        if inside_iif:
            if config:
                str_value = mask_value(raw_value, config)
            else:
                str_value = str(raw_value)
            if isinstance(raw_value, (bool, int, float)):
                formatted = str_value
            else:
                formatted = self._quote_if_string(str_value)
        else:
            if config:
                formatted = mask_value(raw_value, config)
            else:
                formatted = str(raw_value)

        # Применение фильтра (debug или цвет)
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
        Dispatcher for the first pass: chooses the substitution strategy.
        If the template contains iif, uses the slower path with position detection.
        Otherwise uses the fast path.
        """
        if has_iif:
            return self._substitute_with_iif_detection(
                message, var, scope, ctx, state, params
            )
        return self._substitute_simple(message, var, scope, ctx, state, params)

    # ----------------------------------------------------------------
    # Color post‑processing
    # ----------------------------------------------------------------
    def _apply_color_filters(self, text: str) -> str:
        """
        Replaces color markers with actual ANSI codes.

        Looks for patterns __COLOR(color)content__COLOR_END__. The color name
        can be:
        - a simple foreground (e.g., "red")
        - a simple background prefixed with "bg_" (e.g., "bg_red")
        - a combination "foreground_on_background" (e.g., "red_on_blue")

        Args:
            text: string containing color markers.

        Returns:
            String with ANSI codes inserted.

        Raises:
            LogTemplateError: if an unknown color name or component is encountered.
        """
        pattern = re.compile(r"__COLOR\(([a-zA-Z_]+)\)(.*?)__COLOR_END__", re.DOTALL)

        def replacer(match: re.Match[str]) -> str:
            color_name = match.group(1)
            content = match.group(2)

            if color_name.startswith("bg_"):
                # Background only
                bg_name = color_name[3:]
                bg_code = _BG_COLORS.get(bg_name)
                if bg_code is None:
                    raise LogTemplateError(f"Unknown background color: '{bg_name}'")
                ansi_code = f"\033[{bg_code}m"
            elif "_on_" in color_name:
                # Combination: foreground_on_background
                parts = color_name.split("_on_", 1)
                if len(parts) != 2:
                    raise LogTemplateError(f"Invalid color format: '{color_name}'. Use 'foreground_on_background'.")
                fg_name, bg_name = parts
                fg_code = _FG_COLORS.get(fg_name)
                bg_code = _BG_COLORS.get(bg_name)
                if fg_code is None:
                    raise LogTemplateError(f"Unknown foreground color: '{fg_name}'")
                if bg_code is None:
                    raise LogTemplateError(f"Unknown background color: '{bg_name}'")
                ansi_code = f"\033[{fg_code};{bg_code}m"
            else:
                # Simple foreground
                fg_code = _FG_COLORS.get(color_name)
                if fg_code is None:
                    raise LogTemplateError(f"Unknown color: '{color_name}'")
                ansi_code = f"\033[{fg_code}m"

            return f"{ansi_code}{content}{_RESET_CODE}"

        return pattern.sub(replacer, text)

    # ----------------------------------------------------------------
    # Only public method
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
        Performs all variable substitutions and iif evaluation.

        Two passes:
        1. Substitute {%namespace.dotpath} everywhere in the template,
           including inside {iif(...)}. Inside iif, values are formatted as
           literals (strings quoted, numbers and bools as is).
           Color filters (|color) are turned into markers.
           Debug filter (|debug) outputs object introspection.
        2. Evaluate {iif(...)} via ExpressionEvaluator. simpleeval receives
           expressions with already substituted literals and an empty names dict.
           Color functions (red('text')) inside iif return markers.
        3. After both passes, apply color post‑processing to replace markers
           with ANSI codes.

        Args:
            message: template string with variables.
            var: developer‑supplied variables.
            scope: current call scope.
            ctx: execution context.
            state: current pipeline state.
            params: action input parameters.

        Returns:
            String with all substitutions, iif evaluated, and colors applied.

        Raises:
            LogTemplateError: if a variable is not found, namespace unknown,
                              iif is invalid, or access to underscore name.
        """
        has_iif = "{iif(" in message
        # --- Pass 1: substitute {%...} variables, turn colors into markers ---
        resolved = self._substitute_variables(
            message, var, scope, ctx, state, params, has_iif
        )
        # --- Pass 2: evaluate {iif(...)} expressions ---
        if has_iif:
            # Names dict is empty – all values are already inserted as literals.
            resolved = self._evaluator.process_template(resolved, {})
        # --- Pass 3: apply color filters (replace markers with ANSI) ---
        return self._apply_color_filters(resolved)