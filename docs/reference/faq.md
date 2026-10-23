<!-- translated-from: faq_draft.md @ 2026-06-17T15:33:42Z · sha256:1514772f93da -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Questions and answers

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

Here are collected the questions that most often arise for architects and tech leads on first contact with AOA. The answers are grouped by topic, and this is not a retelling of the chapters but an attempt to explain **why** the model is built this way. If you have not yet opened [The system from different altitudes](../explanation/system-altitudes.md) — start with it, much here will become more obvious.

---

## Positioning and boundaries

### Is this a library, a framework, or an architectural style?

AOA is an architectural style, and `aoa-action-machine` is its executable implementation in Python. You can take just the Action Machine core, you can add the FastAPI/MCP adapters, the OCEL plugin, the Maxitor visualizer. What matters is not the packaging but the principle: a business operation is described as an executable contract, not as the sum of agreements around ordinary code.

### When is AOA not needed?

If the code is local, short, and has no external contract — an ordinary function is more honest. AOA starts to pay off when an operation acquires roles, steps, dependencies, rollbacks, audit, cache, transport adapters, a domain model, scenario tests — and the need to explain its behavior to another person or agent. Below that threshold the price of explicitness does not pay back, and there is no point imposing it on yourself.

### How to adopt it in an existing project?

Do not rewrite everything. Take one operation that already hurts: many roles, side effects, rollbacks, an external API, heavy testing. Cast it as an Action, wire up one adapter or one scenario test. If the value did not show on one operation — it is early to scale; if it did show — the next one comes easier, and the decision is made on facts, not faith.

### What is the main trade-off, and won't it be slow?

AOA takes away the freedom of the implicit: you cannot quietly grab the context, silently pull in a dependency, hide a rollback in a random `except`, or keep state in an Action. In return the system becomes predictable, verifiable, and observable. The price is an orchestration layer — checks, events, plugins. For most business operations the cost of the DB, the network, and external services is an order of magnitude higher than this layer, so the price is unnoticeable. Where micro-performance matters, a hot low-level path simply is not cast as an Action: AOA is for operations, not for hot loops.

---

## Why so many declarations

### So many decorators — isn't that noise?

Noise is what does not affect behavior. AOA's decorators affect behavior: `@check_roles` checks access, `@result_*` validates `state`, `@compensate` launches a rollback, `@depends` constrains the dependency factory, `@context_requires` hands out a context slice. These are not comments about intent but intent in executable form. What usually lives in the author's head and surfaces at review here lives in the code and is checked by the machine.

### Why can't we "just agree to write tidy services"?

Agreements work while the team is small and everyone remembers the context. AOA moves the agreement into the grammar of the code. You cannot forget to declare the context and then secretly read it; you cannot get an undeclared dependency; you cannot hide a mandatory rollback in a verbal agreement. The system checks what used to rest on discipline — and discipline scales worse than any tool and is the first to fade as the team grows.

### Where is the boundary between business code and the machine?

Business code lives inside aspects: validation, calculation, a domain service call, assembling the result. The machine is responsible for the uniform mechanics around it: the order of steps, `state`, the checks, roles, dependencies, context, compensations, plugins, cache, events. The boundary is needed so the scenario does not turn into a mix of logic and infrastructure — and so the mechanics can be changed without touching the meaning, and vice versa.

---

## The execution model

### Why are a single entry point and a single result so important?

An operation can be understood if it is clear where it begins and where it ends. In AOA the launch goes through the machine, and the result is returned as a `Result` or through an explicit `@on_error`. This turns the execution graph from a web of calls and side exits into a path you can trace, test, and show on a diagram.

### Why does an Action have no state of its own, and how then does `state` differ from object fields?

An Action must not remember a past call — everything that affects execution comes from the outside: `Params`, `Context`, the pipeline `state`, connections, `@depends`, the machine's plugins. So a test does not "prepare an object" but assembles the input and the environment, and the class of floating bugs where yesterday's call affects today's disappears. `state`, unlike object fields, lives only inside one run: aspects create it, the machine checks it with checkers and passes it on, but after completion it does not become the Action's memory. Intermediate data is observable but does not leak into later calls.

### Why are dependencies and context declared in advance?

A hidden dependency is a hidden cause of changing behavior. `@depends` makes external Actions and resources part of the operation's header: the reader, reviewer, test, and graph see them, and an undeclared dependency `box.resolve(...)` simply will not yield. The same logic for the context: today an aspect reads `user_id`, tomorrow `trace_id`, the day after `request_path`, and nowhere is it visible — `@context_requires` makes the consumption explicit, and the context slice will not let you read the extra.

### Errors: can you no longer raise exceptions?

You can. But if the error is part of a business scenario, it is better to declare it through `@on_error`. Then the order of handlers, the error types, and the fallback path become a visible contract. Handlers are checked top to bottom in declaration order, so there is one rule — the specific before the general: a general `@on_error(Exception)` placed first will shadow a more specific one (the machine does not reorder). No match by type — the original error goes out unchanged.

---

## Data, testing, and audience

### Is an Entity an ORM?

No. An Entity knows nothing of tables, sessions, query builders, or a concrete DB. It is a domain model: fields, relations, partial-loading semantics, lifecycle. Where to take the data from and how to assemble the entity is decided by the resource — PostgreSQL, ClickHouse, S3, an HTTP API, a fixture. So one Action works with one model while the resource implementations change under it.

### Why partial loading instead of separate DTOs per request?

Separate DTOs diverge quickly: the order list returns one shape, the card another, the report a third. AOA lets you return one domain type with different load levels. If the code accidentally touches an unloaded field, it gets a `FieldNotLoadedError` or `RelationNotLoadedError` — not a silent `None` and not a hidden lazy query to the database.

### How to test without huge integration tests?

`TestBench` runs the same Action through the same machines but lets you assemble the needed reality: the user and request context, mocks for `@depends`, connections. You can test the whole Action, one regular aspect, the summary, or a compensator separately — the tests scale by risk. For transactional resources there is rollup: a real scenario is run against the production schema (real INSERT/UPDATE, a real pipeline), but on `commit()` a rollback is done. This is neither a mock nor a dry run but a check against the real schema without saving the changes.

### What does it give a reviewer and an AI agent?

A reviewer sees not only the Python body but the change in intent: roles, dependencies, context, the pipeline, compensators, error handlers, the cache policy. The question shifts from "does the code look fine" to "is the operation's contract declared correctly". An agent gets the system's vocabulary — the Action catalog, descriptions, Pydantic schemas, MCP tools, the dependency graph, the pipeline, and documentation from the code — and does not have to guess from random functions what can be called and with which parameters.

## Relations: specialization

### When do I need specialization rather than another association?

Use it when common information is accompanied by one of several kinds of details. In the record example, a title belongs to every record, but a stamper code belongs to a first pressing and an approval name belongs to a test pressing. The model declares both the possible detail classes and the codes that identify them. An ordinary association describes a reference; writing a union inside it does not add this classifier mapping and its specialization checks. Start with the [complete tutorial](../tutorials/step-21-relations.md#generalization-and-specialization).

### Why not use an enumeration on an ordinary field?

An enumeration or `Literal` is sufficient when only the value differs. Specialization becomes useful when different values correspond to different structures of additional information. It does not require a particular database layout: separate entity classes do not automatically become separate tables.

### Does Generalization mean Python inheritance?

Here it is the reverse link from variant-specific details to their common entity. `FirstPressSpecEntity` inherits `BaseSpecEntity`, and `VinylRecordCoreEntity` inherits `BaseCoreEntity`; the former does not inherit the latter's fields. They describe the same record and share its identity, but hold different fields. To read the title through a loaded reverse link, use `first.record.entity.title`.

### Why are codes declared on both sides?

The dictionary declares the vocabulary once. The head names its type, and each alternative names one declared value on its reverse field. The build proves complete coverage. The mapping is read from those markers, not inferred from class names or union position; dictionary order controls presentation.

### Will selecting FIRST load FirstPressSpecEntity automatically?

No. The declaration makes the correspondence available, but the application or resource must use it to choose what to read and construct. Passing `entity=first` to a container supplies an object already available in memory. Neither the marker nor the container fetches data.

### What does entity=None mean?

The container has no loaded object. Its identifier and, on a specialization link, its variant can still be available. This does not prove that the corresponding record is missing from storage. `Specialization` and `Generalization` expose `.entity` directly, unlike ownership containers that proxy attributes and raise `RelationNotLoadedError` for unloaded access. The [unloaded-link experiment](../../examples/step_21_relations/03_specialization_unloaded.py) prints the actual `None`.

### Does a successful build guarantee that codes in my data are correct?

The build checks declarations, not database rows. Normal construction now also checks each incoming reference: unknown codes and bare strings are refused, and a FIRST variant paired with a RepressSpecEntity is refused. The resource must still resolve storage codes, load the right rows and maintain identifier consistency. See the [runtime examples](../tutorials/step-21-relations.md#an-unknown-variant-is-refused).

### Can two choices on the same entity use different alternatives?

The current closure check still requires every axis to include the classes that generalize to its head. The [working two-axis example](../../examples/step_21_relations/11_specialization_two_axes.py) shares both the dictionary and alternatives; the [subset example](../../examples/step_21_relations/38_error_axis_subset.py) shows the refusal. A dictionary can classify several axes, but this does not remove the restriction on alternative sets. There are no separate classifier fields.

### Can I omit the reverse declaration?

An alternative needs a reverse `Generalization` with a Classifier naming a declared dictionary value for the head's mapping to be valid. Use the paired `Inverse` declarations and descriptions shown in the tutorial. The current validator does not enforce every aspect of inverse-marker mirroring, so an accepted incomplete marker declaration is not evidence that the intended pairing was fully checked. `NoInverse` on an ownership relation is a different feature.

### Why does an invalid model sometimes raise KeyError?

Graph-edge construction can read the code mapping before the specialization validator runs. A missing code can therefore fail there first. For a targeted diagnosis, the [error guide](../how-to/specialization-declaration-fails.md) shows how to call the declaration validator directly. The implementation does not guarantee that every invalid specialization surfaces as `SpecializationDeclarationError` from the machine constructor.

### Does the frame in Maxitor represent another entity?

No. It groups the possible detail classes in the entity–relationship diagram. The entities inside keep their own fields. The frame is a display object and says nothing about a physical table or stored row. The [Maxitor chapter](../tutorials/step-26-maxitor.md#specialization-the-variants-in-one-frame) includes the actual rendered image and explains the frame, dictionary card and generalization arrows.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

### Does every association need an Assoc entity?

No. An association field is a reference between objects. `BaseAssocEntity` describes a separate record whose entire business meaning is the connection between its participants. Service fields such as an identifier or creation timestamp are allowed. Price, quantity or agreement terms give the relationship business content: model that object as Core. An order line with quantity remains Detail because it is an owned part. The [entity tutorial](../tutorials/step-20-entity.md#understand-the-six-kinds) explains these boundaries with runnable examples.

### Does the kind marker enforce the whole domain contract?

No. The hierarchy checks kind inheritance and suffixes when Python creates a class, including undecorated and intermediate classes. It does not infer business meaning from field names, create composite database keys, check equal specialization keys or execute ownership deletion. Existing relationship and lifecycle validators still perform their own checks.

### Why does a dictionary or status declare members with value(...)?

The class does not exist while Python executes its body. `value(...)` explicitly records
arguments for a member; after class creation the framework constructs and validates the
objects. Import it from `aoa.action_machine.domain`. Member access and catalogue lookups
still return shared instances. The old constructor-looking class-name alias is removed;
see the [declaration migration](../tutorials/step-20-dictionaries.md#migrate-an-existing-declaration).

### Why can a dictionary input contain only code while its output contains more?

The code identifies a value already known to the model. The response also carries its
label and properties for consumers that do not have that model. Request
`model_json_schema(mode="validation")` for input and `mode="serialization"` for output.
Use `to_reference()` for JSON-compatible export; a Python-mode `model_dump()` can keep
native date or Decimal objects. The schema describes structure; runtime validation still
checks whether the code belongs to the dictionary.
