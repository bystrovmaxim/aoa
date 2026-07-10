<!-- translated-from: architectural-constitution_draft.md @ 2026-06-25T22:32:46Z (filesystem mtime; draft is gitignored, no git history) · sha256:f4e2ba82ab20 -->
# The AOA Architectural Constitution
## The language of primitives

## Contents

- [Primitives](#primitives)
  - [`BaseSchema` — the typed data contract](#baseschema--the-typed-data-contract)
  - [`BaseAction` — a unit of work](#baseaction--a-unit-of-work)
  - [`BaseEntity` — a domain object](#baseentity--a-domain-object)
  - [`BaseAdapter` — a bridge between systems](#baseadapter--a-bridge-between-systems)
  - [`BaseCoordinator` — extending the machine's behavior](#basecoordinator--extending-the-machines-behavior)
  - [`BaseObserver` — an observer with no right to intervene](#baseobserver--an-observer-with-no-right-to-intervene)
  - [`BaseIntent` — a declaration of intent](#baseintent--a-declaration-of-intent)
  - [`Lifecycle` — a finite state machine](#lifecycle--a-finite-state-machine)
  - [`BaseResource` — a managed, long-lived dependency](#baseresource--a-managed-long-lived-dependency)
- [The choice algorithm](#the-choice-algorithm)
- [Orthogonality](#orthogonality)
- [The final map](#the-final-map)

---

AOA is built on nine fundamental building blocks. Each answers exactly one question: what exactly is this, in the system. If code doesn't fit into any of these slots, that's an architectural error. Clutter shows up immediately.

---

## Primitives

### `BaseSchema` — the typed data contract

The system's data language. An immutable Pydantic model with dot-path navigation and a dict-like interface. Every typed object in AOA descends from it.

| Subclass | Role |
|----------|------|
| `BaseParams` | an Action's input parameters (`frozen`, `extra="forbid"`) |
| `BaseResult` | an Action's result (`frozen`, `extra="forbid"`) |
| `BaseState` | an intermediate execution snapshot (`frozen`, `extra="allow"`) |
| `Context` | a slice of the call's environment (UserInfo + RequestInfo + RuntimeInfo) |
| `BaseEntity` | a domain object (structure + Lifecycle) |

```python
class CreateOrderAction(BaseAction[...]):
    class Params(BaseParams):     # what comes in
        user_id: str

    class Result(BaseResult):     # what goes out
        order_id: str

    class State(BaseState):       # what's visible inside
        created: bool = False
```

`BaseSchema` is the only primitive that other primitives (`BaseEntity`) inherit from.

---

### `BaseAction` — a unit of work

What the system **does**. An operation with an explicit contract: input parameters, an output result, access, rollbacks, dependencies.

```python
class CreateOrderAction(BaseAction[CreateOrderAction.Params, CreateOrderAction.Result]):
    ...
```

---

### `BaseEntity` — a domain object

What the system **models**. A subject-area object with no tie to storage. It knows only its own structure and its `Lifecycle`.

```python
class Order(BaseEntity):
    order_id: str
    status: str
```

---

### `BaseAdapter` — a bridge between systems

How the system **talks to the outside world over a protocol**. A transport layer on top of the same Actions.

```python
class FastApiAdapter(BaseAdapter): ...
class McpAdapter(BaseAdapter): ...
```

---

### `BaseCoordinator` — extending the machine's behavior

How the machine **changes its own behavior**. Coordinators intercept execution phases and can change the result, abort execution, or trigger compensations.

```python
class AuthCoordinator(BaseCoordinator): ...
class CacheCoordinator(BaseCoordinator): ...
class SagaCoordinator(BaseCoordinator): ...
```

---

### `BaseObserver` — an observer with no right to intervene

How the machine **reports on itself**. Observers receive lifecycle events and `box` messages, but **cannot change execution**.

**The key guarantee:** remove every `BaseObserver` descendant, and the system's behavior doesn't change. They're invisible to business logic.

```python
class BaseLogger(BaseObserver): ...           # root of all loggers
class ConsoleLogger(BaseLogger): ...          # box.info → stdout
class KafkaLogger(BaseLogger): ...            # box.info → Kafka

class Plugin(OnIntent, BaseObserver, ABC): ...  # root of all plugins
class OpenTelemetryPlugin(Plugin): ...        # traces and metrics
class OcelPlugin(Plugin): ...                 # object-centric event log
```

`LogCoordinator` and `PluginCoordinator` remain `BaseCoordinator` — they manage the bus and the lifecycle. `BaseLogger` and `Plugin` are observers: they only receive events and react.

| | `BaseCoordinator` | `BaseObserver` |
|---|---|---|
| can change the result | ✅ | ✗ |
| can abort execution | ✅ | ✗ |
| invisibility guarantee | ✗ | ✅ |

---

### `BaseIntent` — a declaration of intent

How a class **declares its participation** in AOA's grammar. An Intent is a mixin that attaches to any primitive and tells the machine: "this class participates in such-and-such protocol."

An Intent carries no behavior — it gives inspectors and coordinators an entry point for discovery and validation.

```python
class CheckRolesIntent(BaseIntent): ...    # the class declares role requirements
class EntityIntent(BaseIntent): ...        # the class participates in the @entity grammar
class CacheIntent(BaseIntent): ...         # the class declares cache_key / on_cache_write
```

An Intent is orthogonal to the other primitives — it can be mixed into `BaseAction`, `BaseEntity`, or any other class.

---

### `Lifecycle` — a finite state machine

The graph of transitions between a domain object's states. A standalone primitive — not a resource, not a coordinator.

```python
class OrderLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("new",       "New").to("confirmed").initial()
        .state("confirmed", "Confirmed").to("shipped").intermediate()
        .state("shipped",   "Shipped").final()
    )
```

---

### `BaseResource` — a managed, long-lived dependency

Anything that lives longer than a single call and is injected via DI (`@depends` / `box.resolve()`). Three kinds, split by one criterion: **who owns the object's lifecycle**.

---

#### `BaseStorage` — I connect to something that exists without me

**Meaning:** the data lives its own life there. You only read and write.

**Constraint:** you can't control its lifecycle. The database existed before you and will remain after.

```python
class OrdersDbManager(BaseStorage): ...    # PostgreSQL
class SessionCacheResource(BaseStorage):   # Redis
class EventQueueResource(BaseStorage):     # Kafka / RabbitMQ
```

---

#### `BaseGateway` — I ask someone else's service to do something

**Meaning:** you delegate the work. You don't know how the service is built inside.

**Constraint:** you can't assume it keeps state for you between calls.

```python
class PaymentServiceResource(BaseGateway):      # Stripe API
class NotificationServiceResource(BaseGateway): # SendGrid
class FraudCheckResource(BaseGateway):          # an external service
```

---

#### `BaseController` — I own this thing, I created it, I'll kill it

**Meaning:** this is an internal core. A compiled LangGraph graph, an in-memory rules engine, a wrapper around legacy code.

**Constraint:** it lives only as long as the process lives. It doesn't persist on its own.

```python
class TicketGraphController(BaseController):    # a compiled LangGraph
class LegacyPricingEngine(BaseController):      # a wrapper around legacy code
class RuleEngineController(BaseController):     # an in-memory rules engine
```

---

## The choice algorithm

The question "where does this go?" stops being a question:

```
Is this input/output data or an execution snapshot?          → BaseSchema (Params / Result / State)
Is this a business decision?                                 → Action
Is this a domain-area model?                                 → Entity
Do you need to store data that lives forever?                → BaseStorage
Do you need to call someone else's service (SMS, payment, API)? → BaseGateway
Do you need to run a local graph, FSM, or legacy engine?      → BaseController
Do you need to change the machine's own behavior?             → BaseCoordinator
Do you need to observe the machine without intervening?       → BaseObserver
Do you need to declare a class's participation in AOA's grammar? → BaseIntent
```

If the code doesn't fit — that's an architectural error, not a special case.

---

## Orthogonality

Primitives don't know about each other. They don't get in each other's way, don't overlap, don't create hidden dependencies.

- `Action` doesn't know which `Adapter` will call it.
- `Action` doesn't know which `Coordinator` is attached to the machine.
- `Action` doesn't know whether `Storage` is implemented on Postgres or MongoDB.
- `Entity` knows nothing at all except its own structure and its `Lifecycle`.

This means any primitive can be replaced without touching the others. The transport changes — business logic is unaffected. Storage changes — the Action doesn't know about it. A coordinator gets added — not a single Action is rewritten.

---

## The final map

```
AOA
├── BaseSchema      — the typed data contract
│   ├── BaseParams     — input parameters
│   ├── BaseResult     — the result
│   ├── BaseState      — an execution snapshot
│   ├── Context        — a slice of the environment
│   └── BaseEntity     — a domain object (↓ see below)
├── BaseAction      — a unit of work
├── BaseEntity      — a domain object
├── BaseAdapter     — a bridge to a protocol
├── BaseCoordinator — extends the machine (changes it)
├── BaseObserver    — observes the machine (side effects only)
├── BaseIntent      — declares participation in AOA's grammar
├── Lifecycle       — a state machine
└── BaseResource    — a managed, long-lived dependency
    ├── BaseStorage    — external, a store (I connect)
    ├── BaseGateway    — external, a service (I delegate)
    └── BaseController — internal (I own)
```
