<!-- translated-from: comparison_draft.md @ 2026-06-17T15:28:31Z · sha256:0c7faa088876 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# AOA next to other frameworks

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [The common pattern](#the-common-pattern)
- [FastAPI](#fastapi)
- [Django](#django)
- [Clean Architecture and DDD](#clean-architecture-and-ddd)
- [CQRS](#cqrs)
- [Temporal, Celery, and workflow engines](#temporal-celery-and-workflow-engines)
- [MVC](#mvc)
- [When to apply AOA](#when-to-apply-aoa)

---

AOA does not compete with FastAPI, Django, or Temporal and does not replace them — more often it works on top. Each of these tools solves its own task excellently; AOA simply puts something else at the center — the operation — and this feels different on the short and the long run.

## The common pattern

The pattern in all the comparisons is one. Many frameworks optimize the **first day**: a quick start, minimum ceremony, code appears in minutes. AOA adds structure from the very beginning and optimizes the **hundredth day** — the moment when the context has evaporated, the team has grown, and there are many operations. This is not "better/worse" but different emphases; often it is more convenient to take both together.

## FastAPI

FastAPI is organized around **endpoints**: a path, a method, a request and response model. For a web API this is superb and gives an instant result — a function with a decorator already works.

AOA is organized around **operations**: what the system can do, regardless of the way it is called. FastAPI answers the question "what HTTP routes do we have", AOA — "what business operations do we have". That is why the transport in AOA is moved into an adapter: one operation is published over HTTP, CLI, or MCP. On the short run FastAPI gets you to a working endpoint faster; on the long run AOA keeps the business logic from dissolving into the transport layer as the system grows. The approaches complement each other: `FastApiAdapter` uses FastAPI as the transport under the operations.

## Django

Django thinks in **models and apps**: the ORM model at the center, around it views, forms, the admin. Where the data structure is the product structure, this is a huge accelerator, especially thanks to the ready ecosystem.

AOA separates the domain model (`Entity`) from storage and puts the operation, not the table, at the center. If a Django model is a mirror of the DB schema, an `Entity` describes a domain object assembled from various sources. The difference is in the thinking: Django asks "what data do we have and how to show it", AOA — "what operations do we have and what they guarantee".

## Clean Architecture and DDD

Conceptually AOA is closest to Clean Architecture and DDD: the same aspirations — separate business logic from infrastructure, make intent explicit. The difference is that in a classic implementation these principles rest on **team discipline**: layers, ports, and adapters are described in conventions, and compliance is checked at review.

AOA translates the same principles into a **verifiable grammar**: the boundary between layers is not an agreement but a construction, harder to break than to keep, and the graph's integrity is checked at startup. Less freedom in *how* to organize the code — more confidence that the organization will not blur over time. In essence, AOA is DDD/Clean with the rules moved out of heads into the machine.

## CQRS

CQRS separates commands (state-changing) from queries (read-only) — at the model level, sometimes the storage level too. It is about **separating the read and write paths**.

AOA does not prescribe CQRS but naturally supports it: a command and a query are simply two operations with different `Params`/`Result`, roles, and dependencies, and both are equally visible in the Action catalog and on the graph. If you need to split reads and writes across different resources — this is solved at the `@depends`/resources level, without changing the operation model. AOA answers not the question "how to separate reads and writes" but the question "how to make each operation readable and verifiable"; CQRS can be built on top, or you can do without it.

## Temporal, Celery, and workflow engines

Orchestrators like Temporal or Celery solve first and foremost the **execution problem**: reliability, retries, distribution, long-running processes. Their sagas and compensations are about resilience of execution over time and across machines.

AOA's sagas and compensations live at a different level — they are about **the readability of intent within one operation**, not about a distributed executor. AOA answers the question "how is this operation built and what is rolled back on failure", not "how to guarantee execution a week from now on a cluster". So they do not exclude each other: an AOA operation can be launched from a Temporal workflow and will remain a readable unit of meaning.

## MVC

MVC arranges code by presentation roles: the controller takes the request, the model holds the data, the view renders. This is a convenient frame for a web application, but the business logic in it usually settles in "fat" controllers or models and is smeared between layers again.

AOA is not about the presentation layer at all — it is about the operation layer beneath it. An MVC controller can simply call an `Action`, keeping the HTTP parsing for itself and handing all the business logic to the operation with its contracts. That is, MVC answers "how to take and show", AOA — "what exactly happens between taking and showing".

## Summary of comparisons

In every pairing AOA answers not the question "what to execute with" but the question "how to express intent so it stays readable and verifiable". That is why it rarely stands *instead of* another framework — more often *next to* it: FastAPI handles transport, Django ORM handles storage, Temporal handles reliable execution, and AOA keeps the business logic assembled and clear. Choosing AOA is not a choice against something but a decision to make the structure of operations the center of the system.

---

## When to apply AOA

**AOA is justified when:**

- the team is growing and new people enter the code — AOA removes the onboarding ritual;
- the business operations are complex: sagas, compensations, distributed transactions;
- observability matters without cluttering the code: plugins, semantic logs;
- you need confidence that architectural rules are followed without constant review;
- AI agents for generating code or tests are planned;
- it is a prototype or MVP: most "temporary" solutions live for years, and structure from day one is cheaper than untangling code written in a hurry;
- from three people and up — it starts to pay off.

**AOA is excessive when:**

- simple CRUD without business logic: a form came in → a record in the DB → a response;
- a project alone or in a pair — probably excessive, though not harmful.

More on the trade-offs — in [Questions and answers](../reference/faq.md); on why the model is built exactly this way — in [Philosophy](philosophy.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
