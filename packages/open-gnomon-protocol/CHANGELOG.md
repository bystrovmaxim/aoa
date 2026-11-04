# Changelog — Open Gnomon Protocol

A version of the protocol is a schema file in [graph/](graph/) that never changes once published. A release is the git tag `open-gnomon-protocol-v<version>`.

## 1.5

A document can say that an action caches its Result entity by entity: a `Cache` node may have the kind `entity_key` — the declaration that builds the key of one entity — and the edge `@cache_entity_key` goes from the action to it. Nothing earlier changes, so a 1.4 document becomes a 1.5 one by changing its `schema_version`. Schema: [graph/1.5.json](graph/1.5.json).

## 1.4

A document can say what a service caches: the node type `Cache`, one per cache declaration of an action, with its `kind` and `description`; the edges `@cache_key`, `@cache_read`, `@cache_write` and `@cache_invalidate` from an action to its declarations; and `caches` and `invalidates` from an action to the entity types its cache entries are tagged with and the ones it drops. Nothing earlier changes, so a 1.3 document becomes a 1.4 one by changing its `schema_version`. Schema: [graph/1.4.json](graph/1.4.json).

## 1.3

A document can say what a service publishes: the node type `Event`, with its fields as `Field` nodes, the edge `@emits` from a method to an event it may publish, the edge `domain_event` from a domain to an event of its vocabulary, and `typed_events` on every `Domain`. `typed_events` is required, so a 1.2 document does not become a 1.3 one by changing its `schema_version`. Schema: [graph/1.3.json](graph/1.3.json).

## 1.2

An entity field, a lifecycle, a role and a `@connection` link may carry their `description`, so a reader can show what the model declares without the model. All four are optional: a 1.1 document becomes a 1.2 one by changing its `schema_version`. Schema: [graph/1.2.json](graph/1.2.json).

## 1.1

Every edge has an `id`, unique among the edges, so two revisions of a graph compare edge by edge. Schema: [graph/1.1.json](graph/1.1.json).

## 1.0

The first shape: a document with `schema_version`, `nodes` and `edges`; every node has an `id`, edges do not. Schema: [graph/1.0.json](graph/1.0.json).
