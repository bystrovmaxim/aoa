## Cross-cutting Logging

ActionMachine provides a built-in cross-cutting logging system that automatically enriches each logger call with execution context: machine name, mode, action, and aspect. The developer receives the `log` parameter of type `ActionBoundLogger` in aspects and can write `await log.info("Message")`, passing additional user data via `**kwargs`.

### Key Concepts

#### 1. Bound Logger (ActionBoundLogger)

**Problem:** Previously, logs lacked information about which action, aspect, and mode they were called from. This made log analysis and filtering difficult in complex scenarios with nested calls.

**Solution:** Introduced the `ActionBoundLogger` class, which is created for each aspect call and automatically adds the following fields to the scope:
- `machine` – machine class name (e.g., `"ActionProductMachine"`).
- `mode` – execution mode (passed to the machine constructor).
- `action` – full action class name (including module).
- `aspect` – aspect method name.

The logging level is passed via the `"level"` key in `var` (added automatically). User data is passed only via `**kwargs` and ends up in `var`; no system fields (except `level`) are automatically added to `var`, preserving the purity of the user context.

#### 2. Logging Coordinator (LogCoordinator)

**Problem:** There were many places in the system where logs needed to be output (aspects, plugins, machine), and each of them had to know about specific loggers. This led to coupling and code duplication.

**Solution:** Created a single coordinator `LogCoordinator` through which all messages pass. The coordinator:
- Accepts a message with a template, variables, scope, context, and other parameters.
- Delegates variable substitution and `iif` expression evaluation to the `VariableSubstitutor` class.
- Broadcasts the final message to all registered loggers, which independently decide whether to process it (via filtering).

#### 3. Console Logger (ConsoleLogger)

**Problem:** During debugging, it is important to quickly distinguish logging levels (info, warning, error, debug) and see the execution context. Plain `print` does not provide such clarity.

**Solution:** Implemented `ConsoleLogger` – a basic logger implementation that outputs messages to `stdout` with support for:
- Indentation by nesting level (`indent`), visually reflecting call depth.
- ANSI coloring:
  - Scope — gray.
  - Levels: `info` — green, `warning` — yellow, `error` — red, `debug` — gray.
  - The unresolved variable marker `<none>` is colored red.

#### 4. Execution Mode (`mode`)

**Problem:** Previously, only the infrastructure environment (`environment` in `Context`) existed, describing the execution environment (host, service version, etc.). However, logging often requires a separate "mode of operation" indicator (production, staging, test, dev) that can influence output format or filtering.

**Solution:** Added a mandatory `mode` parameter to the machine constructor. It is passed to the logger scope and can be used for message filtering. Example values: `"production"`, `"staging"`, `"test"`, `"dev"`. This separates execution mode from the infrastructure environment and provides flexibility in logging configuration.

### Usage in Code

#### 1. Creating a Machine with Logging

```python
from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator

# Create a coordinator with the desired loggers
coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])

# Initialize the machine
machine = ActionProductMachine(
    context=Context(),
    mode="production",
    log_coordinator=coordinator
)
```

If `log_coordinator` is not provided, a coordinator with a single `ConsoleLogger(use_colors=True)` is created automatically.

#### 2. Defining an Action with Aspects Using the Logger

All aspects **must** accept the `log` parameter (sixth). The parameter order is fixed:

```python
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.AspectMethod import aspect, summary_aspect

class MyAction(BaseAction[MyParams, MyResult]):

    @aspect("Data preparation")
    async def prepare(self, params, state, deps, connections, log):
        await log.info("Starting preparation", user=params.user_id)
        # ... logic
        return {"prepared": True}

    @summary_aspect("Result formation")
    async def summary(self, params, state, deps, connections, log):
        await log.debug("Result formed", total=state.get("total"))
        return MyResult(...)
```

#### 3. Logging with Different Levels

```python
await log.info("Informational message", extra="data")
await log.warning("Warning", code=403)
await log.error("Error", exc=repr(e))
await log.debug("Debug information", vars=some_dict)
```

All passed `**kwargs` end up in the `var` dictionary and can be used in message templates (e.g., `"User {%var.user}"`).

#### 4. Log Filtering

Each logger can have a list of regular expressions (`filters`). A message passes the filter if at least one expression matches the string composed of `scope.as_dotpath()`, the message text, and `key=value` pairs from `var`.

Example of creating a logger that accepts only messages from the `ProcessOrderAction` action:

```python
logger = ConsoleLogger(filters=[r"ProcessOrderAction.*"])
```

### Extension: Creating a Custom Logger

**Problem:** The built-in console logger may not suit all cases (e.g., file logging, sending to ELK, integration with external systems).

**Solution:** An abstract base class `BaseLogger` is provided. To create a custom logger, simply inherit from it and implement the asynchronous `write` method:

```python
from action_machine.Logging.base_logger import BaseLogger

class MyLogger(BaseLogger):
    async def write(self, scope, message, var, ctx, state, params, indent):
        # Your implementation (file writing, sending to ELK, etc.)
        ...
```

Then add an instance to the coordinator:

```python
coordinator.add_logger(MyLogger(filters=[...]))
```

### Testing

**Problem:** When testing actions, actual log output should not occur, and we need to verify that logs are called with the correct parameters.

**Solution:** Use `ActionTestMachine` for tests. By default, `mode="test"`. The logger can be replaced with a mock:

```python
from unittest.mock import AsyncMock

mock_coordinator = AsyncMock(spec=LogCoordinator)
machine = ActionTestMachine(ctx=context, mode="test", log_coordinator=mock_coordinator)
```

Now you can check `mock_coordinator.emit` calls and analyze the passed arguments.

### Complete Example

```python
import asyncio
from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.AspectMethod import summary_aspect
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator

class HelloParams(BaseParams):
    name: str

class HelloResult(BaseResult):
    greeting: str

class HelloAction(BaseAction[HelloParams, HelloResult]):
    @summary_aspect("Say hello")
    async def summary(self, params, state, deps, connections, log):
        await log.info("Greeting user", user=params.name)
        return HelloResult(greeting=f"Hello, {params.name}!")

async def main():
    coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
    machine = ActionProductMachine(Context(), mode="dev", log_coordinator=coordinator)
    params = HelloParams(name="World")
    result = await machine.run(HelloAction(), params)
    print(result.greeting)  # Hello, World!

asyncio.run(main())
```

Console output (with colors):
```
[ActionProductMachine.dev.HelloAction.summary] Greeting user user=World
Hello, World!
```