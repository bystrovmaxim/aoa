# Changelog — Open Gnomon Protocol

A version of the protocol is a schema file in [graph/](graph/) that never changes once published. A release is the git tag `open-gnomon-protocol-v<version>`.

## 1.1

Every edge has an `id`, unique among the edges, so two revisions of a graph compare edge by edge. Schema: [graph/1.1.json](graph/1.1.json).

## 1.0

The first shape: a document with `schema_version`, `nodes` and `edges`; every node has an `id`, edges do not. Schema: [graph/1.0.json](graph/1.0.json).
