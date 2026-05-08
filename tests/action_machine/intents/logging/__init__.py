# tests/intents/logging/__init__.py
"""
Tests for the ActionMachine logging subsystem.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers logging components: coordinator, loggers, variable substitution, color filters,
sensitive data masking, and iif constructs.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

LogCoordinator
    Central logging bus. Accepts a message, substitutes variables from five namespaces
    (var, context, params, state, scope), evaluates iif constructs, and fans out to
    registered loggers.

ConsoleLogger
    Logger that writes to stdout. Supports indent by nesting level and optional ANSI colors.

ScopedLogger
    Logger bound to the current aspect or plugin scope. Adds execution coordinates to
    LogScope and forwards to LogCoordinator.

LogScope
    Describes position in the execution pipeline: action, aspect, plugin, nesting level,
    event. Lightweight object with dynamic attributes and dict-like __getitem__ [3].
    Not a pydantic model and does not inherit BaseSchema [3].

VariableSubstitutor
    Template substitution engine [4]. Supports {%namespace.path}, color filters (|red),
    debug filter (|debug), and iif. Nested navigation uses DotPathNavigator.

ExpressionEvaluator
    Safe expression evaluator for iif. Uses simpleeval with builtins (len, upper, lower,
    format_number, color helpers, debug, exists).

@sensitive
    Decorator marking sensitive data; values are masked in logs per configured rules.

═══════════════════════════════════════════════════════════════════════════════
TEST LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/intents/logging/
    ├── __init__.py                     — this file
    ├── test_base_logger.py             — filtering, write parameters
    ├── test_console_logger.py          — console output, indent, colors
    ├── test_log_coordinator.py         — variable substitution, fan-out
    ├── test_log_scope.py               — as_dotpath(), dict access
    ├── test_scoped_logger.py           — aspect and plugin loggers
    ├── test_sensitive_decorator.py     — data masking
    ├── test_color_filters.py           — color filters and functions
    ├── test_debug_filter.py            — |debug filter
    ├── test_expression_evaluator.py    — iif, safe eval
    └── test_variable_substitutor.py    — substitution internals
"""
