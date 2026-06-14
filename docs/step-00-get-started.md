<p align="center">
  <img src="assets/aoa-logo.png" alt="AOA" width="500"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  &nbsp;
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  &nbsp;
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

# Step 00 — Get Started

<p align="center">
  <strong>00 · Get Started</strong> &nbsp;·&nbsp;
  <a href="step-01-action-and-pipeline.md">01 · Action and Pipeline</a> &nbsp;·&nbsp;
  <em>02 · State (coming soon)</em>
</p>

---

AOA — a Python framework for describing business logic through explicit operations. Each operation is a self-contained class with roles, steps, compensations, and contracts. The machine reads these declarations and executes them literally.

This section covers: installation, running the first example, and the tutorial structure.

---

## Installation

### Option A — Use the framework in your own project

```bash
pip install aoa-action-machine
```

This is enough to write and run operations. Optional extensions:

```bash
pip install "aoa-action-machine[fastapi]"   # HTTP API via FastAPI
pip install "aoa-action-machine[mcp]"        # MCP tools for AI agents
pip install "aoa-action-machine[postgres]"   # asyncpg connections
pip install "aoa-action-machine[ocel]"       # OCEL 2.0 event log
```

### Option B — Clone the repository and run examples locally

This option is needed if you're following the tutorial: all examples live in the repo.

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
# Install uv (if not already installed)
pip install uv

# Clone the repository
git clone https://github.com/bystrovmaxim/aoa.git
cd aoa

# Install dependencies
uv sync
```

### Verification

Run the first example:

```bash
uv run python examples/step_01_Action_and_pipeline/01_hello_world.py
```

If `Hello, world!` appears in the console — everything is set up correctly.

---

## Repository structure

```
aoa/
├── docs/                          ← tutorial (you are here)
│   ├── step-00-get-started.md
│   ├── step-01-action-and-pipeline.md
│   └── ...
│
├── examples/                      ← executable examples
│   ├── step_01_Action_and_pipeline/
│   │   ├── 01_hello_world.py
│   │   ├── 02_params_result_and_box.py
│   │   ├── 03_multiple_aspects.py
│   │   └── 04_inheritance.py
│   └── ...
│
└── packages/
    └── aoa-action-machine/        ← framework source code
```

Examples in `examples/` are executable Python scripts, each corresponding to a section in `docs/`. The article explains the concept; the example demonstrates it in working code.

---

## Tutorial

Articles build on each other — it's best to go through them in order.

> The first example will introduce several concepts at once: domain, decorators, Action class, aspect, machine. Don't worry — each one is explained step by step in the article text.

| Step | Article                                                       | Contents                                                                         |
| ---- | ------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 00   | [Get Started](step-00-get-started.md)                         | Installation, structure, this list                                               |
| 01   | [Action and Pipeline](step-01-action-and-pipeline.md)         | Action, aspects, params, result, box, state, inheritance                         |
| 02   | *State: X-ray of the Operation (coming soon)*                 | How state works internally, where it comes from, and how to work with it safely  |

---

<p align="center">
  <strong>00 · Get Started</strong> &nbsp;·&nbsp;
  <a href="step-01-action-and-pipeline.md">01 · Action and Pipeline</a> &nbsp;·&nbsp;
  <em>02 · State (coming soon)</em>
</p>
