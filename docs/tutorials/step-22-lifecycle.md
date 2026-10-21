# Step 22 — Lifecycle: states and allowed transitions

[← Step 21 — Relations](step-21-relations.md) · [Contents](../index.md) · [Step 23 — TestBench →](step-23-testbench.md)

An order may be a draft, paid, or cancelled. A string field can store these words, but it does not say which changes are allowed. A `Lifecycle` describes both the possible states and the transitions between them. For example, a draft may become paid, while a paid order may not return to draft.

A **finite-state machine** (FSM) is a finite set of states with explicit permitted transitions. A **transition** is one allowed move from a current state to a destination. A **lifecycle axis** describes one aspect of an entity's progress. Payment and delivery can be separate axes: an order can be paid while its delivery is still waiting. Each axis has its own states and rules; nothing here automatically synchronizes different axes.

This chapter starts with one small order lifecycle. Every linked script is complete and runs independently; each notebook contains the same case, with definitions, a call, actual output and an explanation. Run scripts from the repository environment:

```bash
uv run python examples/step_22_lifecycle/01_lifecycle.py
```

The Maxitor example additionally needs the workspace's `aoa-maxitor` package and DuckDB. It starts no HTTP server and uses no external database.

## The status description, template and current value

There are three different things to keep separate:

| Thing | What it contains | Example |
| --- | --- | --- |
| Status object | A stable `code`, a human `display_name`, and optional domain fields | The description of `paid` |
| Template | Possible states, their classification and allowed transitions | `draft → paid` |
| Lifecycle instance | A reference to the selected status object, with access to the shared rules | One order currently refers to `DRAFT` |

`BaseStateEntity` supplies the required code and name. A subclass defines any extra fields that this kind of status needs. `StateVocabulary` is a **mixin**: a base class added alongside `Lifecycle` to collect its status attributes and provide lookup by code. The vocabulary is that collection; it is not a second lifecycle or a database table.

A template is built by chained method calls. `.state(DRAFT)` selects the state being described, `.to(PAID)` adds an allowed destination, and `.initial()` finishes that declaration as an initial state. `.intermediate()` marks a state from which work can continue. `.final()` marks a state with no outgoing transitions. This classification belongs to the template, not to fields on the status object.

## Apply one allowed transition

[Python](../../examples/step_22_lifecycle/01_lifecycle.py) · [Notebook](../../examples/step_22_lifecycle/01_lifecycle.ipynb)

This complete declaration uses only two statuses. Paid is final for this particular example; a real order lifecycle may continue to shipping.

```python
from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""


class OrderLifecycle(Lifecycle, StateVocabulary):
    """Allow a draft order to become paid."""

    DRAFT = OrderStateEntity(code="draft", display_name="Draft")
    PAID = OrderStateEntity(code="paid", display_name="Payment received")

    _template = (
        Lifecycle()
        .state(DRAFT).to(PAID).initial()
        .state(PAID).final()
    )

from pydantic import Field
from aoa.action_machine.domain import BaseEntity


class OrderEntity(BaseEntity):
    """Hold the current lifecycle value of one order."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Current order state")
```

The `OrderEntity` field holds an `OrderLifecycle` instance. Create a draft order, request its permitted transition, and put the resulting value into a new entity:

```python
order = OrderEntity(id="ord-1", lifecycle=OrderLifecycle("draft"))
paid = order.lifecycle.transition("paid")
updated = order.model_copy(update={"lifecycle": paid})
assert order.lifecycle.current_state == "draft"
assert updated.lifecycle.current_state == "paid"
assert paid is not order.lifecycle
assert paid.current_status is OrderLifecycle.PAID
assert order.lifecycle.current_status is OrderLifecycle.DRAFT
print("original:", order.lifecycle.current_state)
print("updated:", updated.lifecycle.current_state)
print("final:", updated.lifecycle.is_final)
print("declared target:", paid.current_status is OrderLifecycle.PAID)
```

```text
original: draft
updated: paid
final: True
declared target: True
```

The constructor and `transition()` accept code strings. Each resolves the code to the status object already declared in the template. The new lifecycle refers to `PAID`, while the original still refers to `DRAFT`; neither status is copied or constructed again. `model_copy` puts the new lifecycle into a new order. Nothing is saved to a database by these calls.

`OrderLifecycle("paid")` is also a valid constructor call. Construction checks that the code is in the template; it does not prove that a previous transition happened. Use `transition()` when the current state must constrain the change. AOA does not persist the new value or execute payment, shipping, or other business work merely because a transition was permitted.

## Read the description of the current state

[Python](../../examples/step_22_lifecycle/02_lifecycle_axis.py) · [Notebook](../../examples/step_22_lifecycle/02_lifecycle_axis.ipynb)

A code is suitable for identifying a state, while a screen needs a label and application code may need further information. Add a field to the status class and declare its value on each status:

```python
from pydantic import Field
from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    requires_receipt: bool = Field(default=False, description="Whether a receipt is needed")


class OrderLifecycle(Lifecycle, StateVocabulary):
    """Collect statuses and declare their allowed transition."""

    DRAFT = OrderStateEntity(code="draft", display_name="Draft")
    PAID = OrderStateEntity(code="paid", display_name="Payment received", requires_receipt=True)
    _template = Lifecycle().state(DRAFT).to(PAID).initial().state(PAID).final()
```

The constructor accepts the code read from a database row. Read the selected object directly through `current_status`:

```python
row = {"id": "ord-1", "status": "paid"}
current = OrderLifecycle(row["status"])
status = current.current_status
print("codes:", OrderLifecycle.codes())
print("current code:", current.current_state)
print("label:", status.display_name)
print("requires receipt:", status.requires_receipt)
print("declared object:", status is OrderLifecycle.PAID)
```

```text
codes: ['draft', 'paid']
current code: paid
label: Payment received
requires receipt: True
declared object: True
```

`current_status` returns exactly `OrderLifecycle.PAID`, not a copy. `current_state` returns that object's `code`, so the value to write back to a database remains `"paid"`. Internally there is one reference to the selected object, without a separate stored current code. `requires_receipt` is domain data; reading it does not make AOA issue a receipt or add a transition.

`current_state_info` serves a different purpose: it returns the template's `StateInfo`, including classification and permitted transitions. A status describes the domain meaning; the template determines whether it is initial or final and what may follow it. Lifecycle equality and hashing still use the lifecycle class and code, not the status's additional fields.

`members` is the tuple of declared objects, `codes()` returns their codes in declaration order, and `entity_type` identifies their common class. `by_code(code)` remains useful for looking up an arbitrary code rather than the current state. `by_code("missing")` raises `KeyError`; it does not construct a new status. At runtime, `current.get_state_entity("paid")` reads the description attached to the template and returns `None` for a missing key.

## A known code can still be a forbidden destination

[Python](../../examples/step_22_lifecycle/03_forbidden_transition.py) · [Notebook](../../examples/step_22_lifecycle/03_forbidden_transition.ipynb)

The code `draft` exists, but the example's template provides no route back from `paid`. Checking and attempting that move are different operations:

```python
current = OrderLifecycle("paid")
assert not current.can_transition("draft")
try:
    current.transition("draft")
except InvalidTransitionError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("A final state accepted a transition")
assert current.current_state == "paid"
```

```text
InvalidTransitionError: Transition 'paid' → 'draft' is not allowed on OrderLifecycle. Allowed transitions from 'paid': (no transitions).
```

A valid state code is not automatically an allowed destination. The template declares no outgoing transition from paid, so the runtime rejects the call and keeps the original value.

By contrast, constructing `OrderLifecycle("missing")` fails with `InvalidStateError` because the code itself is absent. That is a separate [script](../../examples/step_22_lifecycle/04_unknown_state.py) and [notebook](../../examples/step_22_lifecycle/04_unknown_state.ipynb):

```text
InvalidStateError: State 'missing' is not defined on OrderLifecycle. Valid states: draft, paid.
```

## What reaches the model graph

[Python](../../examples/step_22_lifecycle/05_graph_attributes.py) · [Notebook](../../examples/step_22_lifecycle/05_graph_attributes.ipynb)

The model graph is AOA's exported description of the application: its entities, operations and their declared relationships. In this example `@entity` registers `OrderEntity` in a small domain; constructing `ActionProductMachine` builds and validates that graph. The linked files include the registration and all imports. They export the graph and select its `paid` state row:

```python
machine = ActionProductMachine(loggers=[])
graph = json.loads(machine.graph_coordinator.to_json())
row = next(node for node in graph["nodes"] if node["type"].startswith("State") and node["properties"]["state_key"] == "paid")
assert row["id"].endswith(":lifecycle:lifecycle:paid")
assert row["label"] == "Payment received"
assert row["properties"]["attributes"]["requires_receipt"] is True
entities = [node for node in graph["nodes"] if node["type"] == "Entity"]
assert len(entities) == 1
print("key:", row["properties"]["state_key"])
print("label:", row["label"])
print("attributes:", row["properties"]["attributes"])
print("model entities:", len(entities))
```

```text
key: paid
label: Payment received
attributes: {'code': 'paid', 'display_name': 'Payment received', 'requires_receipt': True}
model entities: 1
```

The state keeps its code-based identity and receives a human label and JSON attributes. The status type does not become another Entity node: only OrderEntity appears as an entity. Fields excluded with Field(exclude=True) are omitted, and values without a JSON representation prevent export.

Changing the display name changes the label, not the state code. Keep existing codes when migrating if they are already stored or used by callers. Status objects describe possible states; the entity still holds its own current lifecycle value.

## What Maxitor receives

[Python](../../examples/step_22_lifecycle/06_maxitor_states.py) · [Notebook](../../examples/step_22_lifecycle/06_maxitor_states.ipynb)

Maxitor reads the exported graph and produces data for the lifecycle diagram. The example adds `sort_order`, `color`, and `fill_color` as fields on `OrderStateEntity`. These are optional presentation fields, not required fields of `BaseStateEntity`. Draft deliberately has `sort_order=99`, paid has `1`, and cancelled has `2`.

The script loads the real exported graph into `DuckDBGraphResource`, then runs `GetLifecycleFiniteAutomatonAction` through the machine. There is no handwritten sorting in the example. Its observed result is:

```text
state order: ['draft', 'paid', 'cancelled']
paid label: Payment received
diagram attributes: {'code': 'paid', 'color': '#1565c0', 'display_name': 'Payment received', 'fill_color': '#e3f2fd', 'sort_order': 1}
```

This calls Maxitor rather than reproducing its sort in the example. Initial states come first, then integer sort_order (missing or non-integer values count as zero), then code. This is the state-list order, not a guarantee of screen coordinates. The diagram receives only code, display_name, sort_order, color and fill_color; requires_receipt remains in the full graph. The renderer uses color for outlines and fill_color for fills; absent colours use its existing palette.

| Field | How Maxitor uses it |
| --- | --- |
| `display_name` | Supplies the diagram title; the renderer applies its existing title formatting |
| `sort_order` | Orders entries after initial states, with the code breaking ties |
| `color` | Overrides the state outline colour |
| `fill_color` | Overrides the state fill colour |

Without `sort_order`, the existing order is initial states first, then code. Without usable colour values, the existing palette for initial, intermediate and final states applies. Presentation fields do not add transitions or change which states are initial or final. Other domain fields remain available in the full graph but are not part of the diagram response.

## Reuse descriptions without moving the rules into them

[Python](../../examples/step_22_lifecycle/07_inherited_vocabulary.py) · [Notebook](../../examples/step_22_lifecycle/07_inherited_vocabulary.ipynb)

A subclass with no new status declarations and no new template reuses the parent vocabulary and transition rules. This example does not add states to the inherited vocabulary.

```text
['draft', 'paid']
paid
```

[Python](../../examples/step_22_lifecycle/08_classification.py) · [Notebook](../../examples/step_22_lifecycle/08_classification.ipynb)

Use the same paid status as final in one lifecycle and intermediate in another. The status object describes what paid means. Each template decides whether work ends there and where it may continue. A status field must not be treated as an automatic initial/final flag.

```text
first template: FINAL
second template: INTERMEDIATE
```

## When invalid declarations fail

Validation happens at different moments. Creating a status checks its fields. Defining a vocabulary class checks its members. Calling `.state()` or `.to()` checks the argument type immediately, usually while that class body is executing. Building the application graph checks the complete transition structure and exports status fields to JSON. Calling `transition()` checks a move from the current runtime state.

Each refusal below has its own small script and notebook. The examples catch the specific expected error and fail if the invalid declaration is accepted.

| Case | Error and moment | Runnable example |
| --- | --- | --- |
| Reject a blank code | `ValidationError` at object creation | [Python](../../examples/step_22_lifecycle/09_blank_code.py) · [Notebook](../../examples/step_22_lifecycle/09_blank_code.ipynb) |
| Reject a blank display_name | `ValidationError` at object creation | [Python](../../examples/step_22_lifecycle/10_blank_display_name.py) · [Notebook](../../examples/step_22_lifecycle/10_blank_display_name.ipynb) |
| Keep a status object immutable | `ValidationError` at assignment | [Python](../../examples/step_22_lifecycle/11_immutable_status.py) · [Notebook](../../examples/step_22_lifecycle/11_immutable_status.ipynb) |
| Reject duplicate codes in one vocabulary | `ValueError` at class definition | [Python](../../examples/step_22_lifecycle/12_duplicate_code.py) · [Notebook](../../examples/step_22_lifecycle/12_duplicate_code.ipynb) |
| Reject mixed status types | `TypeError` at class definition | [Python](../../examples/step_22_lifecycle/13_mixed_types.py) · [Notebook](../../examples/step_22_lifecycle/13_mixed_types.ipynb) |
| Reject a new template without status attributes | `ValueError` at class definition | [Python](../../examples/step_22_lifecycle/14_empty_vocabulary.py) · [Notebook](../../examples/step_22_lifecycle/14_empty_vocabulary.ipynb) |
| Reject an undeclared transition target | `TypeError` at class definition | [Python](../../examples/step_22_lifecycle/15_foreign_status.py) · [Notebook](../../examples/step_22_lifecycle/15_foreign_status.ipynb) |
| Require Lifecycle beside StateVocabulary | `TypeError` at class definition | [Python](../../examples/step_22_lifecycle/16_mixin_without_lifecycle.py) · [Notebook](../../examples/step_22_lifecycle/16_mixin_without_lifecycle.ipynb) |
| Reject a string in the template | `TypeError` at template call | [Python](../../examples/step_22_lifecycle/17_string_state.py) · [Notebook](../../examples/step_22_lifecycle/17_string_state.ipynb) |
| Reject a string transition target in the template | `TypeError` at template call | [Python](../../examples/step_22_lifecycle/18_string_target.py) · [Notebook](../../examples/step_22_lifecycle/18_string_target.ipynb) |
| Reject a status field without a JSON representation | `PydanticSerializationError` at graph export | [Python](../../examples/step_22_lifecycle/19_non_json_field.py) · [Notebook](../../examples/step_22_lifecycle/19_non_json_field.ipynb) |

The graph's existing structural checks still apply: initial and final states must exist, transitions must point to declared states, final states cannot have outgoing transitions, and the reachability rules must hold. A vocabulary lookup succeeding does not prove that the graph is valid. See the [complete invariant list](../reference/intents-and-invariants.md#lifecycle-fsm).

## A template has no current state

[Python](../../examples/step_22_lifecycle/20_template_current_status.py) · [Notebook](../../examples/step_22_lifecycle/20_template_current_status.ipynb)

`Lifecycle()` builds a template: it describes possibilities without selecting a current status. Reading either `current_state` or `current_status` on that object raises `RuntimeError`. The template remains available for inspection through methods such as `get_states()`; runtime properties require a specialized instance created with a valid code.

```text
RuntimeError: Lifecycle is a template, not an instance. current_state is only available on instances such as Lifecycle('state_key').
RuntimeError: Lifecycle is a template, not an instance. current_status is only available on instances such as Lifecycle('state_key').
```

## Migrating a string-based template

Change the declaration, keeping the existing codes. Move labels into status objects, collect those objects on the lifecycle class, and pass them to the builder:

| Previous declaration or call | Current form |
| --- | --- |
| `.state("draft", "Draft")` | Declare `DRAFT = OrderStateEntity(code="draft", display_name="Draft")`, then use `.state(DRAFT)` |
| `.to("paid")` | Declare `PAID`, then use `.to(PAID)` |
| `OrderLifecycle("draft")` | Unchanged |
| `current.transition("paid")` | Unchanged |
| `current.current_state` | Still a string code |

Keep existing stored codes. The database supplies a code; the lifecycle selects the declared object and exposes its code again through `current_state`. `current_status` adds direct access to the object without changing the existing code-based calls. The vocabulary does not load itself from a database.

## Review and practice

1. Which object describes what `paid` means, and which value says that a particular order is paid?
2. Why does `.to(PAID)` take an object while `transition("paid")` takes a string?
3. Why can the same status be final in one template and intermediate in another?
4. Why does `requires_receipt` appear in the full graph but not the diagram response?

Extend example 01 with `SHIPPED`. Give `PAID` a transition to it and change its classification from `.final()` to `.intermediate()`; declare `SHIPPED` as final. Run `draft → paid → shipped` and check that the original order remains a draft. Adding an outgoing transition while leaving `.final()` in place must fail: classification is explicit, not inferred.

[← Step 21 — Relations](step-21-relations.md) · [Contents](../index.md) · [Step 23 — TestBench →](step-23-testbench.md)
