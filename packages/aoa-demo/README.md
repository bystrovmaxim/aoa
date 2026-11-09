<p align="center">
  <img src="https://raw.githubusercontent.com/bystrovmaxim/aoa/main/docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/tests-87-brightgreen" alt="87 tests">
  <img src="https://img.shields.io/badge/version-3.5.1-informational" alt="3.5.1">
</p>

# aoa-demo: Reference Services for AOA

`aoa-demo` contains two runnable reference services — a FastAPI HTTP service and an MCP server — built on the same domain model: orders, products, and customers. Both services expose the same `Action` operations over different transports, demonstrating how a single piece of business logic is published via `FastApiAdapter` for REST clients and via `McpAdapter` for AI agents without duplicating any logic. The package also serves as the integration fixture used in the AOA test suite.

## The identity domain: one connection per call, with or without a database

`POST /api/v1/identity/lookup` and the MCP tool `identity.lookup` are the reference
for a database-backed resource. The action declares `IdentityStorage` under the
connection key `identity`; the route supplies a value per call — created for the call
and closed after it — so concurrent calls never share a connection and each
transaction belongs to one caller. The domain asks storage for two things — a person,
and a login recorded inside a transaction — and each store supplies them its own way:
over PostgreSQL the domain runs its statements through the driver's protected helpers
(`_execute`, `_fetchrow`) from methods of its own, and in memory it answers from
dictionaries.

It runs in two modes, and only the supplied value differs:

| Mode | When | What the route supplies |
| --- | --- | --- |
| in memory | `AOA_DEMO_POSTGRES_DSN` is unset | `IdentityStubStorage` — the same two operations, no database, no driver |
| over a pool | the variable names a database | `IdentityPostgresStorage(pool=…)` — one connection per call from `IdentityPool` |

`IdentityPool`, a `PostgresPool`, is opened once when the service starts and closed when it stops. An MCP
service has no request-scoped startup hook, but its server has one, so both
transports pass the same `pool_lifespan` to `build()` — no wrapper to write.

```bash
# Database-free: answers from memory; needs no PostgreSQL and no driver.
uv run uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app --port 8000

# Over a pool: install the extra and name the database.
uv add "aoa-demo[postgres]"
AOA_DEMO_POSTGRES_DSN=postgresql://user:pass@localhost/db \
  uv run uvicorn aoa.demo.fastapi_mcp_services.app_fastapi_service:app --port 8000
```

The pool states its size bounds (`min_size=1, max_size=10`) where it is
created; the wait for a free connection is bounded on the pool
(`IdentityPool.acquire_timeout = 30.0`), because `create_pool` has no such parameter
— a `timeout=` there would bound connecting, not waiting.

What each mode is for, and what the resource does with its connection, is in
[`src/aoa/demo/model/identity/README.md`](src/aoa/demo/model/identity/README.md).

## Its databases: a resource is a database

Every demo resource is one database, service or process-owned object, and it lists the entities that lie in it with `@entities`; the machine checks every answer of its public methods against that list. A database is shared by domains, so a resource names no domain: its domains are the domains of the entities it lists.

| Resource | Entities | What it shows |
| --- | --- | --- |
| `ShopDatabaseStorage` (`model/databases/`) | 61 of Store, Support and Inventory | one database of three domains: the storefront, the support desk and the warehouse were three resources of it, and are one now |
| `OutboxPrimaryDatabaseStorage` | 17 of Messaging | the outbox and the dead-letter queue in one database |
| `CatalogObjectStoreStorage`, `CatalogSearchSidecarStorage` | 16 and 1 of Catalog | one domain, two databases, one resource each |
| `IdentityStorage` | 7 of Identity | the identity route's PostgreSQL storage, reached through `IdentityPool` |
| `NotificationGateway`, `CardNetworkGateway` | 1 each | a gateway that reports entities lists them too, and is checked the same way |
| `PaymentGateway`, `TaxQuoteGateway`, `SmtpTransportGateway` and the other gateways | none | a gateway that only calls out declares no `@entities` |

Each other domain keeps its rows in a database of its own (`BillingWarehouseStorage`, `StorefrontSessionCacheStorage`, …). A relation is a fact of the model and joins entities of any databases: a chargeback ticket of the billing warehouse points at the customer order of the shop database it disputes (`ChargebackTicketCoreEntity.order`). The billing warehouse lists the ticket, not the order, so it answers with the order only as a reference, and an action reads the order from the shop database. The graph links each resource to every entity it lists with a `resource_entity` link.

Relations also cross domains, so the model is one piece rather than islands: 17 of them join entities of different domains. The identity's person is the one a support participant, a courier attempt, a delegated work ticket, a custody audit event and a customer account point at; the catalog's product is what an order line orders, a clinical SKU is sold as and a regulated SKU is kept under custody as; a clinical shipment, a freight leg and a telemetry envelope name the warehouse they reach or leave; a logistics handoff carries a customer order; a clearing instruction settles a billing payout plan and an analytics sketch is computed from a billing file. `tests/test_demo_cross_domain_relations.py` keeps at least ten such relations over at least eight domains.

## Its graph history

The demo keeps its graph in [`graph.json`](graph.json), rebuilt by `graph-builder write` with every change of its model, so the file's git history is the graph's history. Paste this link into Maxitor's **AOA Service URL** field to walk through it, compare any two versions, and see the open pull requests after the newest one:

```text
https://github.com/bystrovmaxim/aoa/blob/main/packages/aoa-demo/graph.json?version_link=https%3A%2F%2Fgithub.com%2Fbystrovmaxim%2Faoa%2Fblob%2Fmain%2Fpackages%2Faoa-demo%2Fpyproject.toml&version_key=project.version
```

The version under each point comes from this package's `pyproject.toml`. How to read the track is in [Open a service's graph history](https://github.com/bystrovmaxim/gnomon/blob/main/docs/how-to/open-a-graph-history.md).
