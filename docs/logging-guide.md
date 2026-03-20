# ActionMachine Logging: Practical Guide

## Table of Contents
- [1. Introduction](#1-introduction)
- [2. Setting Up Logging](#2-setting-up-logging)
  - [2.1 Creating a LogCoordinator](#21-creating-a-logcoordinator)
  - [2.2 Adding Loggers](#22-adding-loggers)
  - [2.3 Passing the Coordinator to the Machine](#23-passing-the-coordinator-to-the-machine)
- [3. Using the Logger in Aspects](#3-using-the-logger-in-aspects)
  - [3.1 Aspect Signature](#31-aspect-signature)
  - [3.2 Logging Methods](#32-logging-methods)
  - [3.3 Passing User Data](#33-passing-user-data)
- [4. Template Language in Detail](#4-template-language-in-detail)
  - [4.1 Variables](#41-variables)
    - [Available Namespaces](#available-namespaces)
    - [Dot‑Path Resolution](#dotpath-resolution)
  - [4.2 Conditional Logic with `iif`](#42-conditional-logic-with-iif)
    - [Syntax](#syntax)
    - [Examples](#examples)
    - [Nested `iif`](#nested-iif)
  - [4.3 Color Filters and Functions](#43-color-filters-and-functions)
    - [Filter Syntax (outside `iif`)](#filter-syntax-outside-iif)
    - [Function Syntax (inside `iif`)](#function-syntax-inside-iif)
    - [Available Colors](#available-colors)
  - [4.4 Sensitive Data Masking](#44-sensitive-data-masking)
    - [Using the `@sensitive` Decorator](#using-the-sensitive-decorator)
    - [Parameters](#parameters)
    - [Examples](#examples-1)
  - [4.5 Strict Underscore Rule](#45-strict-underscore-rule)
  - [4.6 Debug Function](#46-debug-function)
  - [4.7 Existence Check (`exists`)](#47-existence-check-exists)
- [5. Log Filtering](#5-log-filtering)
- [6. Creating a Custom Logger](#6-creating-a-custom-logger)
- [7. Testing with Logging](#7-testing-with-logging)
- [8. Complete Example](#8-complete-example)

---

## 1. Introduction

This guide explains how to use the cross‑cutting logging system in ActionMachine. You will learn how to configure loggers, write log messages from aspects, leverage the template language, and extend the system with your own loggers.

---

## 2. Setting Up Logging

### 2.1 Creating a LogCoordinator

The `LogCoordinator` is the central bus. Create one and pass it the loggers you want to use:

from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Logging.console_logger import ConsoleLogger

coordinator = LogCoordinator(loggers=[
    ConsoleLogger(use_colors=True)   # a logger that prints colored messages
])

If you don't provide any loggers, the coordinator will still work (messages are simply discarded).

### 2.2 Adding Loggers

You can add loggers later using `add_logger()`:

from action_machine.Logging.console_logger import ConsoleLogger

plain_logger = ConsoleLogger(use_colors=False)
coordinator.add_logger(plain_logger)

### 2.3 Passing the Coordinator to the Machine

Pass the coordinator to the action machine constructor. If you omit it, a default coordinator with a single `ConsoleLogger(use_colors=True)` is created automatically.

from action_machine.Core.ActionProductMachine import ActionProductMachine

machine = ActionProductMachine(
    mode="production",
    log_coordinator=coordinator
)

The `mode` string (e.g., `"production"`, `"staging"`, `"test"`, `"dev"`) is stored in the logger scope and can be used in templates or filtering.

---

## 3. Using the Logger in Aspects

### 3.1 Aspect Signature

Every aspect method must accept a `log` parameter as the sixth argument. The order is fixed:

from action_machine.Core.AspectMethod import aspect, summary_aspect

@aspect("description")
async def my_aspect(self, params, state, deps, connections, log):
    ...

@summary_aspect("description")
async def my_summary(self, params, state, deps, connections, log):
    ...

### 3.2 Logging Methods

The `log` object provides four asynchronous methods corresponding to standard log levels:

await log.info("Informational message")
await log.warning("Warning message")
await log.error("Error message")
await log.debug("Debug message")

### 3.3 Passing User Data

You can pass additional key‑value pairs that will be available in the template under the `var` namespace:

await log.info("User {%var.name} logged in", name="alice", ip="192.168.1.1")

Inside the template, `{%var.name}` will be replaced with `"alice"`, and `{%var.ip}` with `"192.168.1.1"`. The log level is automatically added as `{%var.level}` (e.g., `"info"`).

---

## 4. Template Language in Detail

### 4.1 Variables

Variables are written as `{%namespace.path}`. The namespace determines the source of the data.

#### Available Namespaces

| Namespace | Source                                                  | Example                       |
|-----------|---------------------------------------------------------|-------------------------------|
| `var`     | User‑supplied kwargs from the log call                  | `{%var.user_id}`              |
| `state`   | Current aspect pipeline state (`BaseState`)             | `{%state.total}`              |
| `scope`   | Logging scope (machine, mode, action, aspect)           | `{%scope.action}`             |
| `context` | Execution context (`Context`)                           | `{%context.user.user_id}`     |
| `params`  | Action input parameters (`BaseParams`)                  | `{%params.amount}`            |

#### Dot‑Path Resolution

All namespaces support nested fields via dot notation:

- `{%context.user.roles}` – accesses `user.roles` inside the `Context`.
- `{%state.order.id}` – accesses `order.id` from the state dictionary.

### 4.2 Conditional Logic with `iif`

#### Syntax

{iif(condition; true_value; false_value)}

- `condition` – a Python‑like expression that can reference variables (as literals). Supported operators: `==`, `!=`, `>`, `<`, `>=`, `<=`, `and`, `or`, `not`, parentheses.
- `true_value` and `false_value` – can be string literals (quoted), numbers, booleans, or variable names.

#### Examples

await log.info("Risk: {iif({%var.amount} > 1000; 'HIGH'; 'LOW')}", amount=1500)
# Output: Risk: HIGH

await log.info("Status: {iif({%state.completed}; 'DONE'; 'PENDING')}")

#### Nested `iif`

expr = "{iif({%var.score} > 90; 'A'; iif({%var.score} > 75; 'B'; 'C'))}"
await log.info(expr, score=82)
# Output: B

### 4.3 Color Filters and Functions

#### Filter Syntax (outside `iif`)

Append a pipe and a color name to any variable:

{%var.amount|red}
{%var.text|bg_blue}
{%var.message|yellow_on_black}

#### Function Syntax (inside `iif`)

Because the pipe character is not allowed inside `iif` expressions, use color functions instead:

{iif({%var.amount} > 10000; red('HIGH'); green('LOW'))}

The functions `red()`, `green()`, `blue()`, etc., return a string wrapped in a color marker.

#### Available Colors

| Foreground          | Background          | Combination example       |
|---------------------|---------------------|---------------------------|
| red                 | bg_red              | red_on_blue               |
| green               | bg_green            | green_on_yellow           |
| yellow              | bg_yellow           | yellow_on_red             |
| blue                | bg_blue             | blue_on_white             |
| magenta             | bg_magenta          | magenta_on_cyan           |
| cyan                | bg_cyan             | cyan_on_black             |
| white               | bg_white            | white_on_red              |
| grey (bright black) | bg_grey             | grey_on_black             |
| orange (bright red) | bg_orange           | orange_on_blue            |
| bright_green        | bg_bright_green     | bright_green_on_black     |
| bright_yellow       | bg_bright_yellow    |                           |
| bright_blue         | bg_bright_blue      |                           |
| bright_magenta      | bg_bright_magenta   |                           |
| bright_cyan         | bg_bright_cyan      |                           |
| bright_white        | bg_bright_white     |                           |

### 4.4 Sensitive Data Masking

#### Using the `@sensitive` Decorator

Apply the decorator to a property getter to automatically mask its value in logs:

from action_machine.Logging.sensitive_decorator import sensitive

class UserAccount:
    def __init__(self, email):
        self._email = email

    @property
    @sensitive(max_chars=3, char='*', max_percent=50)
    def email(self):
        return self._email

#### Parameters

- `enabled` (first, required) – `True` to enable masking, `False` to disable (useful for debugging).
- `max_chars` (default 3) – maximum number of leading characters to show.
- `char` (default '*') – replacement character.
- `max_percent` (default 50) – maximum percentage of the string length to show.

The actual number of shown characters is `min(max_chars, ceil(len(s) * max_percent / 100))`. After the visible part, exactly five replacement characters are appended.

#### Examples

account = UserAccount(email="maxim.bystrov@example.com")
await log.info("Email: {%context.extra.account.email}")
# Output (with max_chars=3, max_percent=50): Email: max*****

# Disabled masking
@property
@sensitive(False)
def email(self):
    return self._email
# Output: Email: maxim.bystrov@example.com

### 4.5 Strict Underscore Rule

If the last segment of a variable path starts with an underscore, accessing it raises `LogTemplateError`. This applies to both fields and properties.

class User:
    def __init__(self):
        self._secret = "value"

user = User()
await log.info("Secret: {%var.user._secret}")   # ❌ LogTemplateError

To log such data, expose it through a public property:

@property
def secret(self):
    return self._secret

await log.info("Secret: {%var.user.secret}")    # ✅ OK

### 4.6 Debug Function

The `debug()` function accepts any object and returns a formatted string showing its public fields and properties. It is intended for debugging and introspection.

**Usage:** Because `debug()` is a function, it must be placed inside a template as part of an `iif` expression (even if the condition is always true). For example:

{iif(1==1; debug(context.user); '')}

**Output format:**

- One line per field/property.
- For each, the name, type, and value are shown.
- If the property is decorated with `@sensitive`, its masking configuration is displayed.
- The output is **non‑recursive** (`max_depth=1`). To inspect a nested object, call `debug` on that object directly.

Example output for `context.user`:

UserInfo:
  user_id: str = "bystrov.maxim"
  roles: list[str] = ["user", "admin"]
  extra: dict = {"org": "acme"}
  email: str (sensitive: max_chars=3, char='*', max_percent=50) = "max*****"

### 4.7 Existence Check (`exists`)

The `exists()` function checks whether a variable is defined in the current evaluation context.

- Inside an `iif` condition, it returns a boolean (`True`/`False`).
- When used as a standalone expression (outside `iif`), it returns the string `"True"` or `"False"`.

**Usage:**

{iif(exists('var.user'); debug(var.user); 'No user')}

Or:

Exists: {exists('var.user')}  -> outputs "True" or "False"

---

## 5. Log Filtering

Each logger can be configured with a list of regular expressions. A message is accepted if at least one expression matches the combined string:

scope.as_dotpath() + " " + message + " " + "key1=value1 key2=value2 …"

Example: a logger that only accepts messages from the `ProcessOrderAction` action, containing the word `error`, or having a `user_id` equal to `123`:

logger = ConsoleLogger(
    filters=[r"ProcessOrderAction.*", r"error", r"user_id=123"]
)

If the filter list is empty or `None`, the logger accepts all messages.

---

## 6. Creating a Custom Logger

1. Subclass `BaseLogger`.
2. Implement the asynchronous `write()` method.
3. Optionally override `supports_colors`.

from action_machine.Logging.base_logger import BaseLogger

class FileLogger(BaseLogger):
    def __init__(self, file_path, filters=None):
        super().__init__(filters)
        self.file_path = file_path

    async def write(self, scope, message, var, ctx, state, params, indent):
        # Write to a file (synchronously or asynchronously)
        with open(self.file_path, 'a') as f:
            f.write(f"{'  ' * indent}{message}\n")

Then add it to the coordinator:

coordinator.add_logger(FileLogger("/tmp/app.log"))

---

## 7. Testing with Logging

When testing actions, you typically don't want actual log output. Use `ActionTestMachine` and replace the log coordinator with a mock.

from unittest.mock import AsyncMock
from action_machine.Core.ActionTestMachine import ActionTestMachine

mock_coordinator = AsyncMock(spec=LogCoordinator)
machine = ActionTestMachine(mode="test", log_coordinator=mock_coordinator)

# Run your action...
await machine.run(context, MyAction(), params)

# Assert that log.emit was called with expected arguments
mock_coordinator.emit.assert_awaited()
call_args = mock_coordinator.emit.call_args
assert "expected text" in call_args.kwargs["message"]

You can also use the `RecordingLogger` from the test suite to capture messages for inspection.

---

## 8. Complete Example

import asyncio
from dataclasses import dataclass
from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.AspectMethod import summary_aspect
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Logging.sensitive_decorator import sensitive

@dataclass
class HelloParams(BaseParams):
    name: str

class HelloResult(BaseResult):
    greeting: str

class UserAccount:
    def __init__(self, name, email):
        self.name = name
        self._email = email

    @property
    @sensitive(True, max_chars=3)
    def email(self):
        return self._email

class HelloAction(BaseAction[HelloParams, HelloResult]):
    @summary_aspect("Say hello")
    async def summary(self, params, state, deps, connections, log):
        # Demonstrate debug() and exists()
        await log.info(
            "Debug user object:\n{iif(1==1; debug(context.user); '')}"
        )
        await log.info(
            "Conditional output: {iif(exists('context.extra.account'); 'Account exists'; 'No account')}"
        )
        await log.info(
            "[{%scope.machine}.{%scope.mode}.{%scope.action}.{%scope.aspect}] "
            "Greeting user {%var.name|green}. Risk: {iif({%var.name} == 'admin'; red('ADMIN'); blue('user'))}",
            name=params.name
        )
        return HelloResult(greeting=f"Hello, {params.name}!")

async def main():
    coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
    machine = ActionProductMachine(mode="dev", log_coordinator=coordinator)

    user = UserAccount(name="World", email="world@example.com")
    context = Context(user=UserInfo(user_id="test"))
    context._extra["account"] = user

    params = HelloParams(name="World")
    result = await machine.run(context, HelloAction(), params)
    print(result.greeting)

asyncio.run(main())

**Console output (colored):**

Debug user object:
UserInfo:
  user_id: str = "test"
  roles: list = []
  extra: dict = {"account": <UserAccount object ...>}
Conditional output: Account exists
[ActionProductMachine.dev.HelloAction.summary] Greeting user World. Risk: user
Hello, World!

If you add `{%context.extra.account.email}` to the template, it will be masked (e.g., `wor*****`).

For an architectural overview and design rationale, see the Logging Architecture document.