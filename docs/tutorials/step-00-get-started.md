<!-- translated-from: step-00-get-started_draft.md @ 2026-06-16T13:35:49Z · sha256:049fdb863bca -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  &nbsp;
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  &nbsp;
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

# Step 00 — Getting started

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-01-action-and-pipeline.md">Step 01 — Action and the pipeline →</a></td>
</tr></table>

- [What AOA is](#what-aoa-is)
- [How to read this guide](#how-to-read-this-guide)
- [Installation](#installation)
- [Repository structure](#repository-structure)

---

This is an introductory chapter. There is not a single line of business code here — only a conversation about what problem AOA solves, how the guide is arranged, and setting up the workspace. We get to the first operation in the next chapter; for now let's agree on the words and install the tools.

---

## What AOA is

Every program does something. It places an order, accrues interest, makes a payment — and while the system is young, these actions are clearly visible in the code. But the system lives on, and around each action grows what has nothing to do with the action itself: a permission check, a log write, error handling, a conversation with the database and the network. A year passes — and to understand what an operation does, you have to read it whole, separating the wheat from the chaff. While the context is fresh and kept in the author's head, this is tolerable. The trouble comes later: memory fades, the team grows, and knowledge of the system stays in the heads of a few. Conventions and code review hold the decay back unreliably — agreements get broken, and the carriers of context become a bottleneck.

AOA answers this differently. Every operation here is a self-contained entity, a class named `Action`. It has a typed input (`Params`), a typed output (`Result`), and a straight chain of steps between them — no branches, no hidden exits. Access, dependencies, contracts on intermediate data — the operation declares all of it openly, in its own header. And — most importantly — these declarations are checked not by a human at review but by the machine itself: some at system startup, some at execution time. A convention that used to live in oral tradition becomes an invariant that cannot be bypassed: break it, and the system will not come up and will tell you exactly what is wrong.

Hence the name — Action-Oriented Architecture, an architecture built around operations. Three of its words will accompany us the whole way:

- **Action** — a business operation cast as a class. A unit of meaning you can read whole.
- **Pipeline** — the sequence of an operation's steps, executed strictly top to bottom, without branches.
- **Machine** (`ActionProductMachine`) — the executor that reads an operation's declarations and leads it through the pipeline.

Later these words will fill with code. For now it is enough to grasp the general idea: AOA moves the rules out of heads and comments into the very fabric of the program and takes it upon itself to guard them.

---

## How to read this guide

The chapters build up, and the order matters: each rests on the previous one. The full map is on the **[Contents](../index.md)** page.

Each chapter comes with a folder of executable examples in the `examples/` directory. These are not pseudocode or pictures, but programs that run and give exactly the output quoted in the text. The surest way to master the model is to go in a circle: read a section, run the example, check the output, then break something in the example and see how the behavior changes. The AOA model is built so that it reveals itself more vividly on deviations than on successful runs.

---

## Installation

There are two paths. Which one is yours depends on whether you are reading this for work or for acquaintance.

### Option A — the framework as a dependency of your project

If you need AOA in your work:

```bash
pip install aoa-action-machine
```

This is enough to write and run operations. Everything else — transport adapters, observability plugins, ready-made resources — is wired in as needed and collected in the **[Ready extensions](../index.md#ready-extensions)** reference. The most common ones install like this:

```bash
pip install aoa-fastapi-adapter   # HTTP API via FastAPI
pip install aoa-mcp-adapter       # MCP tools for AI agents
pip install "aoa-action-machine[postgres]"   # asyncpg connections
pip install aoa-ocel                  # OCEL 2.0 event log
```

### Option B — the repository with examples

This path is for going through the guide: all the examples live in the repository, and it is more convenient to work right with them. You will need Python 3.12 or newer and [uv](https://docs.astral.sh/uv/getting-started/installation/) — an environment manager that will create an isolated environment and install the dependencies itself.

```bash
pip install uv
git clone https://github.com/bystrovmaxim/aoa.git
cd aoa
uv sync
```

### Verification

Run the first example:

```bash
uv run python examples/step_01_Action_and_pipeline/01_hello_world.py
```

`uv run` executes Python inside the created environment — no need to activate it by hand. A `Hello, world!` line in the console means everything is in place. If you get an error instead, it is almost always a matter of the Python version (3.12+ is required) or of the command being run not from the repository root.

---

## Repository structure

AOA is a monorepo. At the top level everything splits in two: the three packages the framework is assembled from, and the scaffolding around them — documentation, examples, tests, infrastructure. Let's descend this pyramid exactly two layers: first the general map, then into the core the next chapter works with. There is no need to go deeper now (the separate modules of `aoa-examples` and `aoa-maxitor`, the execution-core files) — that lives in the respective packages' READMEs and in the reference.

### Top level: packages and scaffolding

```
aoa/
├── packages/        ← the three packages AOA is assembled from
│   ├── aoa-action-machine/   ← CORE: the Action model, execution core, contracts, observability
│   ├── aoa-examples/         ← LIBRARY of ready-made domains — the framework "at scale"
│   └── aoa-maxitor/          ← VISUALIZER: graph, ERD, and diagrams straight from code
│
├── docs/            ← this guide (chapters + the intents-and-invariants reference)
├── examples/        ← executable examples for the chapters (end-to-end scenarios + step_01/step_02)
├── tests/           ← around two thousand tests; part of the invariants are also checked here
├── scripts/         ← static checks of package and layer boundaries for CI
│
├── README.md · ROADMAP.md · LICENSE
├── pyproject.toml · uv.lock      ← the uv workspace
└── housekeeping: .github/, dist/, .venv, caches, htmlcov
```

There is little to keep in mind. The center of gravity is `packages/`, and there are three different worlds there: `aoa-action-machine` — the core itself, where the next chapter begins; `aoa-examples` — a large library of ready-made domains, where the framework is seen "at scale" (its inner workings are in the package README); `aoa-maxitor` — a tool that builds an interactive map of the system from code. `docs/` and `examples/` go in pairs: a chapter explains an idea, an example shows it at work. And `tests/` and `scripts/` are notable in that a significant part of the AOA invariants are checked exactly there — statically, before production.

### Second level: inside the core

From here on we will need only `aoa-action-machine`. Its sources lie in `src/aoa/action_machine/` and split into recognizable subsystems:

```
action_machine/
├── model/          ← base classes: BaseAction, BaseParams, BaseResult, BaseEntity
├── domain/         ← BaseDomain
├── intents/        ← intent decorators, the vocabulary of the AOA language:
│                       @meta, @check_roles, @regular_aspect, @summary_aspect,
│                       @result_* (checkers), @compensate, @on_error,
│                       @depends, @connection, @context_requires, @sensitive, @entity
├── runtime/        ← the execution core: the machine, pipeline run, sagas,
│                       error handling, role checking, cache, dependencies
├── graph/          ← the system graph of operations and its inspectors
│   graph_model/
├── plugin/         ← lifecycle observers: core, open_telemetry, ocel
├── logging/        ← box, Channel, ConsoleLogger, LogCoordinator
├── resources/      ← the boundary with the external world: postgres, sql, external_service
├── adapters/       ← transports: fastapi, mcp
├── testing/        ← TestBench — tests by substituting the world
└── auth/ · context/ · exceptions/ · …  ← roles, the call environment, contract errors
```

This map is for growing into: most of the subsystems will unfold in their own chapters — sagas, errors, dependencies, plugins, resources, testing. For now it is enough to hold on to three of them: `model/`, `intents/`, and `runtime/`. It is exactly from these that the first operation is assembled — and that is what we turn to next.

The setup is over. Next — the first operation.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-01-action-and-pipeline.md">Step 01 — Action and the pipeline →</a></td>
</tr></table>
