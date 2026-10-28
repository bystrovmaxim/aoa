# Open Gnomon Protocol

How a service keeps its graph in a file, so that the file can travel with every change and git can hold the graph's history. This folder is the standard; [`maxitor-gnomon`](../README.md) is one implementation of it, and anything that reads or writes these files the same way is another.

## The graph document

A graph document is one JSON object:

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | yes | the version of this protocol the document follows, e.g. `"1.1"` |
| `nodes` | yes | an array of objects; each has an `id`, unique among the nodes |
| `edges` | yes | an array of objects; from `1.1` on each has an `id`, unique among the edges |

The exact shape of each version is its JSON Schema, [`graph/<version>.json`](graph/). A document is a graph of version *V* when it declares `"schema_version": "V"` and passes `graph/V.json`.

## Versions

| Version | Schema | What changed |
|---|---|---|
| `1.0` | [graph/1.0.json](graph/1.0.json) | the first shape: nodes have an `id`, edges do not |
| `1.1` | [graph/1.1.json](graph/1.1.json) | every edge has an `id`, so two versions of a graph compare edge by edge |

**A published version never changes.** A new shape of the graph is a new version and a new file; readers keep reading the old ones. Each schema's `$id` is its address in this folder.

## Comparing two versions of a graph

Elements are matched by `id`, never by position: a node or an edge that moved within its array has not changed. Two documents differ by the elements added, removed or changed under the same `id`.

## The graph file

A graph is kept in a file as its document written with sorted keys, an indent of two spaces, non-ASCII characters as they are, and one newline at the end, in UTF-8. The same graph therefore always gives the same bytes, and a file changes only when its graph does. The file holds the graph and nothing else.

## The config

A repository lists its graphs in `gnomon.toml`, whose shape is [config/1.0.json](config/1.0.json):

```toml
gnomon = "1.0"                      # the config's own version

[[graph]]
name  = "demo"                      # unique; names the graph
cwd   = "."                         # optional, default "." — where the build runs
build = "python -m my_service.print_graph"   # prints the graph document to standard output
file  = "my_service/graph.json"             # unique — where the graph is kept
```

Paths are relative to the config's folder. Each graph is built in a process of its own.
