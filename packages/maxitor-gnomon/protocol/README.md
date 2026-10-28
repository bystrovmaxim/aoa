# Open Gnomon Protocol

**Describe a project's model in a shared language, then make that description part of the project.**

Imagine opening an unfamiliar service and finding a description of its model: which domains it contains, which entities it works with, which actions it exposes and how those parts relate. A person can inspect that description; a viewer or coding agent can read the same document. They share the meaning of an entity, an action and a dependency because the format defines those concepts.

Open Gnomon Protocol gives that description a standard form: a graph. Model elements are nodes, relationships are edges, and their types and properties say what each element means. For example, “placing an order requires checking stock” becomes two `Action` nodes connected by a `@depends` edge.

We are building two things:

1. **A standard for describing models.** The protocol defines the vocabulary and JSON format that producers and consumers agree on. A project exports its model once in that format; tools can read the description without importing the project's code. The versioned JSON Schemas in this folder define the accepted documents.
2. **A first skill for project initiation: [`gnomon-setup`](../skills/gnomon-setup/SKILL.md).** The skill helps a coding agent put that standard to work in a repository: find its model export, establish a repeatable build, save the model description and connect a check that keeps it current.

The standard answers **“How do we describe the model?”** The skill answers **“How do we set this up in our project?”** Once configured, the project follows this workflow:

```text
Project model → build command → graph.json → review alongside the code
                                    ↑
                         CI checks that it is current
```

The saved document becomes a common input for tools that understand the protocol. Keeping it beside the code also makes changes visible: when an action gains a dependency, the exported graph gains an edge. The code and the updated model description can be reviewed in the same pull request, and Git records the model's history.

[`maxitor-gnomon`](../README.md) implements the protocol through the `gnomon` command. AOA is the first producer. Other producers can participate by exporting documents that pass the same schemas.

## Get started

### 1. Ask your coding agent to set up the project

Open the repository you want to configure and give your agent this request:

> Set up this project's model graph and graph history using the gnomon-setup skill at https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/maxitor-gnomon/skills/gnomon-setup/SKILL.md

The skill works with a project that can export its model as a graph document. It inspects the repository, proves a build command for each graph and asks you which graphs to include and where to save them. Project initiation here means setting up model export and its checks in your repository; the project needs a model and a producer capable of exporting it.

If your agent already has the skill installed, ask it to **run `gnomon-setup`**. For installation commands or setup by hand, see the [implementation's getting-started guide](../README.md#three-ways-to-start).

### 2. Review the setup

After you confirm the graphs and their locations, the skill prepares:

| Result | Purpose |
|---|---|
| `gnomon.toml` at the repository root | Lists each graph, its build command and its output file. |
| A `graph.json` for each selected service | Stores that service's model description in the standard format. |
| A CI step running `gnomon check` | Rebuilds the graphs and fails if the saved files are stale or missing, or a build fails validation. |

Setup ends with a passing `gnomon check`. The skill leaves the changes for you to review and commit. Running it again audits the existing setup.

### 3. Keep the model current as you work

With `gnomon` available through your project's tool environment:

```bash
gnomon write   # Rebuild the graphs and update their saved files.
gnomon check   # Verify that the saved files match; write nothing.
```

Review the graph changes with the code changes and commit them together. CI runs `gnomon check` on subsequent changes, and Git holds the model's history.

## What a model description looks like

Here is a small model: `PlaceOrder` depends on `CheckStock`. Both actions are nodes; the dependency is an edge with its own identity.

```json
{
  "schema_version": "1.1",
  "nodes": [
    {
      "id": "shop.PlaceOrder",
      "type": "Action",
      "label": "Place order",
      "properties": {"description": "Place a customer order."}
    },
    {
      "id": "shop.CheckStock",
      "type": "Action",
      "label": "Check stock",
      "properties": {"description": "Check that ordered items are available."}
    }
  ],
  "edges": [
    {
      "id": "shop.PlaceOrder.depends.CheckStock",
      "source_id": "shop.PlaceOrder",
      "target_id": "shop.CheckStock",
      "type": "@depends",
      "relationship": "Serving",
      "is_dag": true,
      "properties": {"description": "Check availability before placing the order."}
    }
  ]
}
```

Save this illustration as `model.json` and validate it:

```text
$ gnomon validate model.json
ok 1.1: 2 nodes, 1 edges
```

In a configured project, the build command produces the document and `gnomon write` saves it. The schema defines the supported node and edge types and the properties required for each; adding arbitrary objects with an `id` is not enough.

## Protocol reference

### Graph document

A graph document is one JSON object:

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | yes | The graph schema version, such as `"1.1"`. |
| `nodes` | yes | Model elements, each with an `id` unique among nodes, a `type`, a `label` and `properties`. |
| `edges` | yes | Relationships between nodes, with source and target IDs, a type and properties; from `1.1` onward, each also has an `id` unique among edges. |

The exact shape of each version is its [JSON Schema](graph/). A document declares `"schema_version": "V"` and must pass `graph/V.json`.

### Versions

| Version | Schema | What changed |
|---|---|---|
| `1.0` | [graph/1.0.json](graph/1.0.json) | The first shape: nodes have an `id`, edges do not. |
| `1.1` | [graph/1.1.json](graph/1.1.json) | Every edge has an `id`, so two versions of a graph compare edge by edge. |

**A published version never changes.** A new shape requires a new version and a new schema file; readers keep reading the old ones. Each schema's `$id` is its address in this folder.

### Comparing model revisions

Elements are matched by `id`, never by position: moving a node or an edge within its array does not change that element. Two documents differ by the elements added, removed or changed under the same `id`. Stable IDs let a reviewer follow an element across model revisions.

### Graph file

The saved graph is the document encoded as UTF-8, with sorted object keys, an indent of two spaces, non-ASCII characters preserved and one newline at the end. The file contains only the graph. The same document produces the same bytes; this formatting does not reorder the node or edge arrays.

### Project config

A repository lists its graphs in `gnomon.toml`, whose shape is [config/1.0.json](config/1.0.json):

```toml
gnomon = "1.0"                              # The config's own version.

[[graph]]
name  = "shop"                              # Unique graph name.
cwd   = "."                                 # Optional; defaults to ".".
build = "python -m shop.build_graph"         # Prints only the graph document.
file  = "shop/graph.json"                    # Unique output file path.
```

The config version is independent of the graph schema version: this `1.0` config can point to a build that emits a `1.1` graph. Paths are relative to the config's folder. Each graph is built in a separate process.
