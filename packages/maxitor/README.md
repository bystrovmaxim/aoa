<p align="center">
  <img src="https://raw.githubusercontent.com/bystrovmaxim/aoa/main/docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/tests-193-brightgreen" alt="193 tests">
  <a href="client/README.md"><img src="https://img.shields.io/badge/SPA-React%2019%20·%20Vite-61dafb?logo=react&logoColor=white" alt="Maxitor client"></a>
  <img src="https://img.shields.io/badge/Node.js-22-339933?logo=node.js&logoColor=white" alt="Node 22">
  <img src="https://img.shields.io/badge/version-2.3.0-informational" alt="2.3.0">
</p>

# maxitor: A System You Can See

Most architecture diagrams live in Confluence or Miro and go stale faster than they are drawn. A month after release the schema no longer matches reality: new domains appear, operation steps are renamed, dependencies change. The gap between what is written and what runs is a familiar problem.

**Maxitor** breaks that cycle: diagrams are not drawn by hand. They are generated from the same code that actually runs. Code changes — the diagram changes. Open a browser — see the current system. Diagrams stay current because they are built from the same intents that execute in code. Intent changes — the diagram reflects it.

## What Is Maxitor

Maxitor is a React SPA that turns AOA project code into live interactive diagrams. The data source is not YAML or Confluence annotations — it is the code itself: domains, actions, dependencies, entities, lifecycle state machines. Everything declared in code via intents automatically appears in the graph.

Maxitor can show four views of the system:


| View            | Shows                                                                       |
| --------------- | --------------------------------------------------------------------------- |
| **Full graph**  | Everything: domains, Actions, pipeline steps, resources, dependencies, links |
| **ERD**         | Entities, fields, relations, and cardinality by domain                      |
| **Use case**    | Roles and Actions each role can access                                      |
| **Lifecycle**   | Finite state machine for a specific entity                                  |


---

## 1. Full Graph: The Whole System as One Map

The full graph is an interactive network of all elements in an AOA system. One view shows what used to take days of onboarding.

<p align="center">
  <img src="../../docs/assets/maxitor-full-graph.png" alt="Full graph of an AOA system" width="900">
</p>

The graph shows nodes of different types, each with a color label:

- **Domain** — groups Actions by business area
- **Action** — business operation with name and description
- **RegularAspect / SummaryAspect** — pipeline steps inside an Action
- **Compensator** — rollback steps (saga)
- **ErrorHandler** — error handlers
- **Resource** — dependencies via `@depends`
- **Entity / EntityField** — data model
- **Lifecycle** — state machine
- **Role** — access roles
- **Params / Result / Field** — contract of each Action

The left panel filters by groups: Applications, Domains, Roles, Actions, Entities, Resources. The graph is interactive — zoom, pan, isolate a cluster. On every diagram a drag, a two-finger swipe or a plain mouse wheel moves the picture, and a pinch or Ctrl / ⌘ + wheel zooms it, as design tools do.

**Key effect**: a new developer understands system structure in five minutes without reading code. A reviewer sees what changed without diffs across dozens of files.

---

## 2. ERD: Data Model From Code

The ERD tab shows entity schemas by domain: fields, types, relations, cardinality.

<p align="center">
  <img src="../../docs/assets/maxitor-domain-erd.png" alt="ERD — entity schema by domain" width="900">
</p>

The left panel navigates domains. For each domain:

- **Entity domain view** — ERD for that domain only
- **Use case view** — roles and Actions in the domain

On the diagram you see:

- Which entities belong to the domain
- Their fields — all of them, whatever 1-hop shows — and their types as one clean name (`str | None`, a relation by its target, `X[]` for many), the full annotation in the row's tooltip ([example](../../examples/step_26_maxitor/10_field_types.py), [notebook](../../examples/step_26_maxitor/10_field_types.ipynb))
- How entities are linked (`AssociationOne/Many`, `AggregateOne/Many`, `CompositeOne/Many`): one line per association, every line whose two tables are on screen, each end with its cardinality — exactly one, zero or one (a relation that may hold nothing), zero or many — and its role, the field on that side, shown while the line is hovered; a specialization's extensions keep a dashed line to their head, ending the same way, with no arrows
- Header color — domain membership; the white icon beside the name — the entity's kind

One filter panel, with **Domains** and **Kinds** folding like an accordion, hides or shows tables by domain and by kind; Kinds lists the kinds of the tables on this diagram and is shown when there are at least two. Hovering a table dims the others; hovering a line or a key field marks the fields it joins and keeps bright only the tables it joins; clicking a table or field name copies it. The whole walk-through is [Step 26 — Read and filter the ERD](../../docs/tutorials/step-26-maxitor.md#read-and-filter-the-erd).

The ERD is built from classes inheriting an entity kind base and their relation fields. Each exported Entity node carries `properties.entity_kind` and the kind's name, `properties.entity_kind_label`; Maxitor preserves both in the `entity` table and keeps no list of kinds of its own, so a graph from another producer shows its own kinds. A row with no kind loads as `unknown`; a kind word without a name is named by the word capitalised ([example](../../examples/step_26_maxitor/06_entity_kinds.py), [notebook](../../examples/step_26_maxitor/06_entity_kinds.ipynb)). This distinguishes independent objects, technical associations, owned parts, specializations and reference values. State types are excluded from ordinary Entity nodes and belong to lifecycle diagrams instead.

Kind metadata does not yet hide technical associations on its own. Rebuild graph exports created before the required property was introduced. The [graph-to-store example](../../examples/step_20_entity/11_graph_kind.py) ([notebook](../../examples/step_20_entity/11_graph_kind.ipynb)) demonstrates the value arriving unchanged in Maxitor.

### A closed dictionary, and a field that references one

A dictionary is an Entity node whose `entity_kind` is `enum`; it carries `properties.values`, the values it declares, each one its reference object `{code, display_name, properties}`. The ERD card does not draw them: it is an ordinary card of the dictionary's own fields, with no value rows, no codes and nothing standing in their place. The values stay in the graph and in the ERD response for every consumer that reads them, so a catalogue with ninety-three entries no longer sets the height of the diagram.

A field typed by a dictionary carries `reference_qualname`, the dictionary's interchange id. The card shows the field's type; the line from that row to the dictionary's table says what it references. The axis container's label names the dictionary that classifies it.

The ERD payload still carries each value's `code`, `display_name` and descriptive `properties` as name/value text items, in declaration order and in the strict response shape; the full graph retains their original object form. The card draws none of it. The renderer names no domain-specific field, and an ordinary entity has an empty value list.

Dictionary references arrive from the graph in JSON form, including any declared field
serializer's output. The server converts properties to `{name, value}` text items for
the strict ERD response schema; strings stay text and other values use JSON notation.
A saved graph that already includes those properties needs no rebuild for this display.

The server also supplies each specialization group's complete `label`, such as
`pressing (by VinylRecordKindEnumEntity)`. The client displays it once. `dictionary_label`
is no longer a member of the ERD group response; it remains model metadata on the graph
edge. The [group-label example](../../examples/step_21_relations/51_group_label.py) and
[notebook](../../examples/step_21_relations/51_group_label.ipynb) print the actual response.

See the [dictionary example](../../examples/step_20_dictionaries/09_erd.py) and [Maxitor tutorial](../../docs/tutorials/step-26-maxitor.md#dictionaries-in-the-entity-diagram) for the actual output.

---

## 3. Use Case: Who Can Do What

The use case view shows roles and Actions they can access via `@check_roles`. This is not hand-written documentation — it is read directly from `@check_roles` annotations in code.

<p align="center">
  <img src="../../docs/assets/maxitor-use-case.png" alt="Use case diagram — roles and Actions" width="900">
</p>

Useful for:

- Access audits — see who can run which operations
- Business discussions — answer “can a manager do this?” without opening code
- Reviewing role changes

---

## 4. Lifecycle: State Machine

For each entity with a `Lifecycle` field, Maxitor builds a finite automaton graph: states, transitions, initial and final vertices.

<p align="center">
  <img src="../../docs/assets/maxitor-life-cycle.png" alt="Lifecycle finite state machine for an entity" width="900">
</p>

Especially valuable when an entity lifecycle is non-trivial — e.g. an order with a dozen states. Instead of reading automaton code line by line, you see the full transition graph.

Endpoint: `GET /api/v1/lifecycle-finite-automaton?entity_qualname=...`

---

## 5. How It Works Inside

Maxitor itself is an AOA application. Its backend is written with Actions, wired through `FastApiAdapter`, and uses DuckDB to store a graph snapshot.

```
AOA code (domains, Actions, entities)
        ↓
NodeGraphCoordinator — walks all elements
        ↓
GraphStore — one DuckDB snapshot per source (?source=)
        ↓
GraphSourceMiddleware → FastAPI Actions → JSON endpoints
        ↓
React SPA (G6 + Graphviz WASM)
```

On backend startup, `NodeGraphCoordinator` scans all registered AOA code and builds the process graph. A diagram read names the AOA service it wants as `?source=<graph-json URL>`; the graph store builds that service's DuckDB snapshot on the first read and keeps it, so a repeat open costs nothing and two users of two services never see each other's graph. At most 50 graphs are held — a built graph stays until then, kept current with its service — and at most 4 builds run at once.

**Important**: the React SPA is fully separate from the backend. Two independent processes. In production you can build static SPA assets and serve them from a CDN, with the API hosted separately.

---

## 6. API Endpoints

All diagram endpoints are AOA Actions exposed via `FastApiAdapter`:

Every diagram read names the source it is for:

```
GET /api/health                          — health check, plus the store's load

GET /api/sidebar?source=<url>            — navigation: domains, entities

GET /api/v1/full-graph?source=<url>      — full graph (G6 payload)
GET /api/v1/list-domains?source=<url>    — domain list with colors
GET /api/v1/list-entities?source=<url>   — ERD slice by domain
GET /api/v1/list-entity-kinds?source=<url> — the graph's entity kinds and their names
GET /api/v1/list-node-types?source=<url> — graph node types
GET /api/v1/domain-use-case-diagram?source=<url>&domain_id=…
GET /api/v1/lifecycle-finite-automaton?source=<url>&lifecycle_graph_node_id=…

GET /api/v1/graph-fingerprint?source=<url> — which graph is held for the source, from memory

GET /api/meta/app-info                   — the running version and client build

WS  /api/v1/rooms/{room_id}/live         — a room: everyone looking at one service together

POST /api/load  {"service_url": "<url>"} — rebuild that one source
```

Every successful `GET` carries an `ETag` of its content; a request that sends it back in `If-None-Match` gets `304` with no body.

Maxitor serves its own model too, as any AOA service does: `GET /examples/model/graph-json` is an AOA action, so Maxitor's own address typed into the service field opens Maxitor's own diagram.

`source` is the AOA service's `graph-json` URL, URL-encoded. A read that names no source answers `400` and says which parameter is missing; a source that cannot be built answers `422` with the reason; a server with no free build slot answers `503` with `Retry-After` and the client retries. A read whose source is not built yet builds it on the spot — it never answers "not loaded".

`POST /api/load` is not "load into the slot" any more: it rebuilds the source it names and leaves every other source alone. In the SPA the same action is the **"Reload from service"** button next to the open source; a deep link only reads and never reloads.

`GET /api/health` reports the store, so an operator can watch it without a debugger:

```json
{"status": "ok", "graphs_held": 3, "builds_running": 4, "builds_queued": 2}
```

Swagger UI: `http://127.0.0.1:8000/docs`

JSON from endpoints can be embedded in your portal, CI pipeline, or documentation tooling. A runnable tour of every case — two sources side by side, `400`, `422`, `503`, reload, eviction, a burst — is [examples/step_26_maxitor/02_api_graph_per_source.py](../../examples/step_26_maxitor/02_api_graph_per_source.py) and its [notebook](../../examples/step_26_maxitor/02_api_graph_per_source.ipynb).

**Held graphs stay current.** While someone looks at a graph, Maxitor asks its service whether it changed — every 30 seconds when the service gives `ETag` or `Last-Modified` (an unchanged one answers `304`), every 2 minutes when it does not (the body's SHA-256 is compared). A changed service is rebuilt in the background and replaces the old graph only when the build succeeded; a service that is down keeps the graph everyone has. Open pages redraw by themselves, keeping page, filters, zoom and centre. A built graph stays until `MAXITOR_MAX_GRAPHS` is reached. Tour: [09_fresh_graphs.py](../../examples/step_26_maxitor/09_fresh_graphs.py) · [notebook](../../examples/step_26_maxitor/09_fresh_graphs.ipynb).

**Rooms.** **Open room** in the top row gives a link; whoever opens it joins after giving a name. Everyone in the room sees the others' pointers on the same spot of the diagram, filters and layout modes are shared per page — the opener's own become the room's, and inside a room only the room's values show — a click on someone's circle goes to them, and **Follow** keeps your screen where theirs is, gliding rather than jumping, always at your own zoom, and shows you what they hover, select and open. A pointer stays while its person is in the room, however long it stands still. A room holds 20 people and a process 100 rooms; a room ends two minutes after its last person leaves, and its link then opens the page on its own. Every room operation is an AOA action; pointers are relayed without one and never logged. Tour: [08_rooms.py](../../examples/step_26_maxitor/08_rooms.py) · [notebook](../../examples/step_26_maxitor/08_rooms.ipynb).

---

## 7. How to Run

### Backend

```bash
uv run task maxitor-api
```

Starts FastAPI at `http://127.0.0.1:8000`. Environment:

| Variable | Default | Meaning |
|---|---|---|
| `MAXITOR_API_HOST` | `127.0.0.1` | where uvicorn listens |
| `MAXITOR_API_PORT` | `8000` | port |
| `MAXITOR_MAX_GRAPHS` | `50` | most graphs one process holds; a built graph stays until this many are held, then the least recently read leaves |
| `MAXITOR_MAX_CONCURRENT_BUILDS` | `4` | builds running at once; further reads wait, then get `503` |
| `MAXITOR_ROOM_ORIGINS` | — | extra browser origins allowed to join a room, comma separated; a page of the same host as Maxitor needs none |

A held graph is much smaller than it used to be. The build keeps no index and no primary key, because no diagram query reads through one: the reference service's graph takes about 13 MiB of database memory (43.5 before #268), and the process gains about 24.5 MiB per graph on macOS and 16.7 MiB on Linux. At the default limit of fifty graphs that is roughly 1.1 GiB of process instead of 2.7. The diagrams and their timings are unchanged, and the build is slightly faster. A graph that lists the same node id twice in one table is still refused, now with a message that names the id and the table.

Memory after a graph is dropped depends on the system. On Linux the process returns it: with ten reference graphs held the process was about 309 MiB, and about 192 MiB after all were dropped. On macOS the process keeps its peak and reuses it, so there the process size is set by the most graphs held at once. DuckDB's `allocator_bulk_deallocation_flush_threshold` and `allocator_flush_threshold` lower the Linux peak by 10–35 MiB but do not change the answer; the measurement is in `specs/025-graph-index-memory/research.md` (R10).

### Frontend (dev)

```bash
cd packages/maxitor/client
npm install
npm run dev
```

SPA at `http://127.0.0.1:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`.

### Production

```bash
VITE_MAXITOR_API_BASE_URL=https://api.example.com npm run build
```

Builds static SPA assets. Deploy: SPA on CDN or nginx, API in a separate container.

Rooms run over a WebSocket. A reverse proxy in front of Maxitor must pass the upgrade through and keep the page's `Host`, or a browser is refused with `4403`; for nginx, in the `location` that proxies Maxitor (or a `location /api/v1/rooms/` of its own):

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header Host $host;
proxy_read_timeout 1h;
```

`proxy_read_timeout` keeps a quiet room connection open; without it nginx closes it after a minute and the page reconnects.

---

## 8. Client Architecture (`client/src`)

The React SPA is layered:


| Layer                  | Contents                                                          |
| ---------------------- | ----------------------------------------------------------------- |
| `app/`                 | Entry: `App.tsx`, `AppProviders.tsx`. No business logic           |
| `components/`          | All UI: `layout/`, `pages/`, `navigation/`, `diagrams/`          |
| `components/diagrams/` | `FullGraphViewer/` (G6), `ErdViewer/` (Graphviz WASM)             |
| `api/`                 | HTTP clients mirroring FastAPI routes                             |
| `model/`               | TypeScript contracts between UI and API                           |
| `lib/`                 | Pure helpers, layout constants                                    |
| `styles/`              | MUI theme                                                         |


Graph rendering:

- **G6** (`@antv/g6`) — full graph, force-directed layout
- **`@hpcc-js/wasm-graphviz`** — ERD, deterministic Graphviz layout

---

## 9. Installation

```bash
pip install maxitor
# or in the monorepo
uv sync
```

Dependencies: `aoa-action-machine`, `fastapi`, `uvicorn`, `duckdb`.

## 10. Graph files: the `gnomon` command

`pip install maxitor` with no extra installs only this part — no AOA, no server.

**See every change to your system's model in the pull request that makes it.**

A diff shows which lines of code changed. It does not show what that did to the system: a new dependency, a renamed domain, an action wired into another application. `maxitor-gnomon` makes CI say it. Here is `gnomon check` on the AOA demo whose saved graph is one change behind its code:

```text
$ gnomon check
stale demo: packages/aoa-demo/graph.json
  edges[id=aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain.TelemetryPipelineDomain|application|aoa.action_machine.application.application.Application]: added
  nodes[id=aoa.demo.model.store.store_domain.StoreDomain].label: Shop → StoreDomain
run: gnomon write --config gnomon.toml, and commit the graph files
```

Each service exports its model — domains, entities, actions and their dependencies — in the [Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/protocol/README.md), and keeps it in one file, `graph.json`, beside its code. `gnomon` rebuilds those files from the code and fails CI when one is stale. So:

- **reviewers see the model change**, element by element, next to the code that changed it;
- **the model never drifts**: the code produces it, nobody draws it by hand;
- **git holds the model's history** — `git log -p graph.json` is how the system grew;
- **any tool reads the project without running it** — a viewer such as [Maxitor](https://github.com/bystrovmaxim/aoa/blob/main/packages/maxitor/README.md), an architecture check, a coding agent.

`maxitor-gnomon` knows nothing about any framework. [AOA](https://github.com/bystrovmaxim/aoa) services export the protocol out of the box; any service that can print a graph by its schema works the same way.

### Installation

```bash
pip install maxitor
```

or run it without installing, with [uv](https://docs.astral.sh/uv/): `uvx --from maxitor gnomon --version`. Python 3.12+.

### Get started

#### The fastest way: one sentence to your coding agent

> Set up this project's model graphs with the skill at https://raw.githubusercontent.com/bystrovmaxim/aoa/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/skills/gnomon-setup/SKILL.md

The agent installs the `gnomon-setup` skill and runs it. The skill finds every service, proves how each one's model is exported — writing a small exporter where a service has a model but nothing prints it — and shows you one table: each service, its build, its proof, where its file goes. Nothing changes until you answer. Then it writes `gnomon.toml`, saves the graphs and adds the CI check, and leaves the result for you to review and commit.

Already have the package? `gnomon skill > .claude/skills/gnomon-setup/SKILL.md` (or `.cursor/skills/…`), then ask the agent to *run gnomon-setup*. Run it again any time: on a configured project it is an audit.

#### By hand, in four steps

**1. Export each service's model** — a command that prints its graph and nothing else. For an AOA service:

```python
# my_service/build_graph.py
import importlib
import sys

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator


def main() -> None:
    importlib.import_module("my_service.app")   # registers the service's actions, entities and resources
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()
```

**2. List the graphs** in `gnomon.toml` at the repository root:

```toml
gnomon = "1.0"

[[graph]]
name  = "my-service"
build = "uv run python -m my_service.build_graph"
file  = "my_service/graph.json"
```

**3. Write them** — `gnomon write` — and commit `gnomon.toml` with the graph files.

**4. Check them in CI:**

```yaml
- uses: astral-sh/setup-uv@v5
- run: uv sync
- name: The model graphs are current
  run: uvx --from "maxitor==3.0.0" gnomon check
```

### Day to day

1. Change the code.
2. Run `gnomon write` — or let your check run do it as its last step.
3. Commit the changed `graph.json` with the code.
4. CI runs `gnomon check`. It rebuilds every graph, writes nothing, and fails on a stale file — naming what changed and the command that fixes it.

Forgot step 2? Run `gnomon write`, commit, push: one more commit to the same pull request.

### Commands

| Command | |
|---|---|
| `gnomon write` | Rebuild every graph; write each file whose content changed. An unchanged graph leaves its file untouched. |
| `gnomon check` | Rebuild every graph; write nothing; fail if a file is stale or missing, or a build fails. |
| `gnomon validate <file \| ->` | Say whether a document is a graph of the version it declares: `ok 1.1: 3213 nodes, 4841 edges`. |
| `gnomon skill` | Print the `gnomon-setup` skill for coding agents. |

`write` and `check` take `--config FILE` (default `gnomon.toml`). Each graph is built in a process of its own, with a 300-second limit. Exit codes: `0` all good · `1` a graph is stale, missing or broken · `2` the config is refused.

The same graph always gives the same bytes, so a file changes only when the model does. Differences are matched by `id` and read *what the file holds → what the code builds*; when only a file's layout differs, `check` says `only the formatting differs`.

### Configuration

| Key in `[[graph]]` | |
|---|---|
| `name` | Unique; names the graph in every message. |
| `build` | Shell command that prints the graph, and only it. |
| `file` | Unique; where the graph is kept. |
| `cwd` | Optional, default `.`; where the build runs. |

Paths are relative to `gnomon.toml`. A wrong config is refused by graph and field — `graph 'demo', file: required` — before anything is built.

### Keeping graphs in a repository

The [Open Gnomon Protocol](../open-gnomon-protocol/README.md) defines the graph document. How a repository keeps its graphs — one file per service, listed in `gnomon.toml`, checked in CI — is this command's convention, below.

#### The graph file

- A service keeps its graph in one file, conventionally `graph.json` in the service's folder.
- The file MUST hold the document and nothing else, in UTF-8, with object keys sorted, an indent of two spaces, non-ASCII characters as they are, and one newline at the end — `json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"`. The same document therefore always gives the same bytes. The formatting MUST NOT reorder `nodes` or `edges`.
- The file MUST be written by the service's build, never edited by hand. It SHOULD change in the same pull request as the code that changed the model, and CI SHOULD check that it is current.

#### The project configuration

A repository lists its graphs in `gnomon.toml` at its root ([its schema](src/maxitor/gnomon/config_schema.json)):

```toml
gnomon = "1.0"                         # the configuration's own version

[[graph]]
name  = "shop"                         # unique
cwd   = "."                            # optional, default "."
build = "python -m shop.build_graph"   # prints the graph document, and only it
file  = "shop/graph.json"              # unique
```

- Relative paths start at the configuration's folder; absolute paths are allowed.
- A build MUST exit with 0 and print exactly one graph document; otherwise it produced no graph and nothing is written. Each graph MUST be built in a process of its own, so that two services' models never mix.
- The configuration's version is independent of the graph's.

#### A conforming repository

A repository conforms when it lists its graphs in `gnomon.toml`, keeps each file as above, and checks in CI that every file is current.

### From Python

```python
from maxitor.gnomon.schemas import check_graph, graph_schema
from maxitor.gnomon.config import read_config

check_graph(document)       # None, or GraphRefused("graph 1.1 at edges/3: 'id' is a required property")
graph_schema("1.1")         # the JSON Schema of a protocol version
read_config("gnomon.toml")  # the repository's graphs, or ConfigRefused
```

A graph of thousands of elements is checked in a fraction of a second.

### Learn more

- **[Open Gnomon Protocol](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/protocol/README.md)** — the language itself: the document, its vocabulary, versions, identity and conformance
- **[gnomon-setup](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/skills/gnomon-setup/SKILL.md)** — the skill an agent follows
- **[Every case, runnable](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/examples/step_26_maxitor/12_graph_file.py)** — a saved graph, a rebuild, a stale copy, an unknown version
- [Changelog](https://github.com/bystrovmaxim/aoa/blob/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon/CHANGELOG.md) · [Source](https://github.com/bystrovmaxim/aoa/tree/maxitor-gnomon-v0.1.0/packages/maxitor-gnomon) · [Issues](https://github.com/bystrovmaxim/aoa/issues)

Apache License 2.0.
