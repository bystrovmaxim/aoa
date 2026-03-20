# Cross‑Cutting Logging in ActionMachine: Architecture Overview

## Table of Contents
- [1. Introduction](#1-introduction)
- [2. Problems Solved](#2-problems-solved)
- [3. Core Components](#3-core-components)
  - [3.1 ActionBoundLogger – Bound Logger](#31-actionboundlogger--bound-logger)
  - [3.2 LogCoordinator – Logging Bus](#32-logcoordinator--logging-bus)
  - [3.3 ConsoleLogger – Console Output](#33-consolelogger--console-output)
  - [3.4 Execution Mode (`mode`)](#34-execution-mode-mode)
- [4. Template Language Capabilities](#4-template-language-capabilities)
  - [4.1 Variable Substitution](#41-variable-substitution)
  - [4.2 Conditional Logic (`iif`)](#42-conditional-logic-iif)
  - [4.3 Color Filters](#43-color-filters)
  - [4.4 Sensitive Data Masking](#44-sensitive-data-masking)
  - [4.5 Strict Underscore Rule](#45-strict-underscore-rule)
- [5. How It Works – Data Flow](#5-how-it-works--data-flow)
- [6. Extensibility](#6-extensibility)

---

## 1. Introduction

ActionMachine provides a built‑in cross‑cutting logging system that automatically enriches each log message with execution context: machine name, mode, action, and aspect. It is designed to be:

- **Context‑aware** – logs contain information about where they were emitted.
- **Flexible** – multiple loggers can be attached, each with its own filtering rules.
- **Secure** – sensitive data can be automatically masked, and access to underscored names is forbidden.
- **Expressive** – a rich template language supports variables, conditional logic, and colors.

This document explains the architectural decisions behind the system and how its components interact.

---

## 2. Problems Solved

### 2.1 Lack of Execution Context in Logs

In a system with nested actions, aspects, and plugins, it was hard to understand which part of the pipeline produced a given log message. Without context, debugging and monitoring became cumbersome.

**Solution:** Every logger call is bound to the current execution scope (machine, mode, action, aspect). This context is automatically added to each message and can be used for filtering or displayed in the log output.

### 2.2 Scattered Logging Logic

Logging was called from many places (aspects, plugins, the machine itself), leading to code duplication and tight coupling to specific loggers.

**Solution:** A single logging bus – the `LogCoordinator` – centralizes message distribution. Components only need to know the coordinator; they don't care which loggers are attached.

### 2.3 Inflexible Output Formatting

Developers needed control over log formatting (colors, indentation, prefixes) and the ability to send logs to different destinations (console, file, ELK).

**Solution:** Loggers are pluggable. A base class `BaseLogger` defines the interface, and concrete implementations (like `ConsoleLogger`) can be added to the coordinator. Formatting is delegated to the logger, and messages can be filtered using regular expressions.

### 2.4 Security Risks – Sensitive Data Leakage

Logging often inadvertently exposes sensitive information (emails, credit card numbers, etc.). Manually redacting such data is error‑prone and repetitive.

**Solution:** A declarative `@sensitive` decorator marks property getters whose values should be masked in logs. Masking parameters (how many characters to show, replacement symbol, maximum percentage) are defined once and automatically applied wherever the property is used in a log template.

### 2.5 Accidental Exposure of Private Fields

Developers might accidentally log private fields (names starting with `_`). Such fields are usually not meant for public output.

**Solution:** A strict rule forbids accessing any variable whose last segment begins with an underscore. If such access is attempted, `LogTemplateError` is raised immediately, preventing accidental data leaks.

### 2.6 Need for Different Execution Modes

Logging behaviour may differ between development, testing, staging, and production. For example, in development you may want verbose, colored output, while in production you may want JSON‑formatted logs.

**Solution:** The machine constructor accepts a mandatory `mode` parameter (e.g., `"dev"`, `"test"`, `"staging"`, `"production"`). This value is passed to the logger scope and can be used to adjust formatting or filtering.

---

## 3. Core Components

### 3.1 ActionBoundLogger – Bound Logger

Each aspect call receives a `log` parameter of type `ActionBoundLogger`. This logger automatically captures the current execution context and stores it in a `LogScope` object:

- `machine` – class name of the action machine (e.g., `"ActionProductMachine"`).
- `mode` – execution mode passed to the machine.
- `action` – full class name of the action (including module).
- `aspect` – name of the aspect method.

When the developer calls `log.info(...)`, the bound logger:

- Removes any user‑supplied `level` key (to avoid overriding the system level).
- Adds the level (`"info"`, `"warning"`, etc.) to the `var` dictionary.
- Forwards the message, `var`, `scope`, and other parameters to the `LogCoordinator`.

### 3.2 LogCoordinator – Logging Bus

`LogCoordinator` is the central hub that all log messages pass through. Its responsibilities:

- Maintain a list of registered loggers.
- Accept a message (with template, variables, scope, context, etc.).
- Delegate variable substitution and `iif` evaluation to `VariableSubstitutor`.
- Broadcast the final string to every logger that accepts the message (according to its filters).

The coordinator does **not** filter messages itself; filtering is done independently by each logger.

### 3.3 ConsoleLogger – Console Output

`ConsoleLogger` is a ready‑to‑use logger that prints messages to `stdout`. Features:

- **Indentation** – based on the nesting level (`indent` parameter), each level adds two spaces.
- **Color support** – when `use_colors=True`, ANSI codes are preserved; when `False`, they are stripped (by the coordinator).
- **No automatic prefix** – users must explicitly include scope variables in their templates (e.g., `[{%scope.machine}.{%scope.mode}.{%scope.action}.{%scope.aspect}]`).

### 3.4 Execution Mode (`mode`)

The `mode` parameter is a string passed to the machine constructor (e.g., `"production"`, `"staging"`, `"test"`, `"dev"`). It is stored in the logger scope and can be used for:

- Conditional formatting (e.g., show more details in `dev` mode).
- Filtering (e.g., a logger that only accepts messages from `production` mode).
- Routing (e.g., send `production` logs to a remote service, `dev` logs to console).

---

## 4. Template Language Capabilities

The logging system supports a rich template language inside message strings. Below is an overview of its features; detailed syntax and examples are in the [Logging Guide](logging-guide.md).

### 4.1 Variable Substitution

Variables are written as `{%namespace.path}`. Supported namespaces:

- `var` – developer‑supplied dictionary (from `**kwargs`).
- `state` – current aspect pipeline state (`BaseState`).
- `scope` – logging scope (machine, mode, action, aspect).
- `context` – execution context (`Context`).
- `params` – action input parameters (`BaseParams`).

Nested fields are accessed via dot notation, e.g., `{%context.user.user_id}`.

### 4.2 Conditional Logic (`iif`)

Inline conditionals use the syntax `{iif(condition; true_value; false_value)}`. The condition is a Python‑like expression that can reference variables (as literals). Branches can be string literals or variables.

Example: `{iif({%var.amount} > 1000; 'HIGH'; 'LOW')}`

### 4.3 Color Filters

Any substituted value can be wrapped with a color filter using a pipe:

- Foreground: `{%var.amount|red}`
- Background: `{%var.text|bg_red}`
- Combination: `{%var.text|red_on_blue}`

Inside `iif`, color functions (e.g., `red('text')`) are used instead of filters, because the pipe syntax is not supported in expressions.

Available colors: `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `grey`, `orange` and their bright variants (e.g., `bright_green`). Background versions are prefixed with `bg_`.

### 4.4 Sensitive Data Masking

Properties decorated with `@sensitive` are automatically masked when used in templates. The decorator accepts parameters:

- `max_chars` – maximum number of leading characters to show.
- `char` – replacement character.
- `max_percent` – maximum percentage of the string length to show.

Masking is applied after the value is converted to a string. The result shows the first `min(max_chars, ceil(len(s) * max_percent / 100))` characters, followed by exactly five replacement characters.

### 4.5 Strict Underscore Rule

If the last segment of a variable path starts with an underscore (`_` or `__`), accessing it raises `LogTemplateError`. This prevents accidental logging of private fields. To log such data, expose it through a public property.

---

## 5. How It Works – Data Flow

1. An aspect calls `await log.info(template, **kwargs)`.
2. `ActionBoundLogger` creates a `LogScope` (machine, mode, action, aspect) and forwards the call to `LogCoordinator.emit()`.
3. `LogCoordinator` passes the template, `var` (with added `level`), scope, context, state, params, and indent to `VariableSubstitutor.substitute()`.
4. `VariableSubstitutor` performs two passes:
   - First, it replaces all `{%namespace.path}` patterns with their string representations. Inside `iif` blocks, values are formatted as literals (strings quoted, numbers as is). Color filters are turned into markers (`__COLOR(color)value__COLOR_END__`).
   - Second, it evaluates all `{iif(...)}` expressions using `ExpressionEvaluator` (which relies on the safe `simpleeval` library). Color functions inside `iif` return markers.
   - Finally, it replaces markers with actual ANSI codes (if the target logger supports colors).
5. The coordinator iterates over all registered loggers and, for each one:
   - Checks whether the message passes the logger’s filters (regex matching against `scope.as_dotpath() + " " + message + " " + "key=value …"`).
   - If the logger does not support colors (`supports_colors == False`), ANSI codes are stripped using `BaseLogger.strip_ansi_codes()`.
   - Calls `logger.handle()`, which eventually invokes the logger’s `write()` method.

---

## 6. Extensibility

To create a custom logger, subclass `BaseLogger` and implement the asynchronous `write()` method:

```python
from action_machine.Logging.base_logger import BaseLogger

class MyLogger(BaseLogger):
    async def write(self, scope, message, var, ctx, state, params, indent):
        # Send message to file, ELK, etc.
        ...
If the logger can handle ANSI colors, override the supports_colors property to return True. The coordinator will then preserve color markers when passing the message.

Loggers can be added to the coordinator at any time via coordinator.add_logger().

For detailed usage instructions, examples, and API reference, see the Logging Guide.