# Research: A resource is a database

Why the design in [plan.md](plan.md) looks the way it does, and what else was considered.

## The check is a method wrapper, not a proxy

**Decision**: `BaseResource.__init_subclass__` wraps each public method of a declared resource class once; the resource object itself is handed over unchanged.

**Rationale**: `box.resolve(…)`, `connections[…]` and a test-bench substitute all end up as the same object, so wrapping the object's own methods covers all three entry points without a proxy. A proxy would break `isinstance`, identity comparisons in existing tests and attribute access on the real object; it would also have to be composed with the per-kind nesting wrappers of #486 (`SqlStorageWrapper` deliberately exposes no query member to a nested action). A method wrapper costs one call per public method, keeps the class identity, and leaves the nesting wrappers untouched.

**Alternatives considered**: a generic proxy around every handed-over resource — rejected on identity and composition; decorating at call sites — rejected because `connections` and substitutes are not known at declaration.

## Exact class, and a reference is an unloaded relation

**Decision**: the walk compares `type(value)` with the listed classes. A subclass of a listed class is refused. A relation that leads out of the list passes only unloaded — its container holds the id and no entity; that is the reference of the issue. A loaded entity of a class outside the list is refused, even a partial one that holds only its id. A partial answer of a listed class is that class and passes. Dictionary members and lifecycle states belong to the model and pass.

**Rationale**: the maintainer's answer: the resource declared concrete classes and returns exactly what it promised; entities are not subclassed in the model, and a shorter answer is a partial of the same class. AOA already has the reference: a relation container holds its id always and its entity only when loaded, and reading through an unloaded one raises `RelationNotLoadedError`. Using that container state gives "a relation that leads out of the list comes back as a reference" a precise, testable shape, with no rule about which fields a partial entity set. A relation to a dictionary holds its members loaded by design, so dictionary members and lifecycle states cannot be judged by the list.

**Alternatives considered**: `isinstance` semantics — rejected: a subclass could carry relations the plan never saw; a separate `Reference` type — rejected: it would change how a resource is written; an id-only partial entity as the reference — rejected: it makes a loaded relation pass by the fields it happens to hold.

## The plan is data, computed once

**Decision**: `_entities_plan` is a frozen value kept in each concrete resource class's own `__dict__`: the listed classes and, for each, whether a relation reachable from it leaves the list. It is never inherited; the wrapper reads it for `type(self)`, and a resource wrapper reads the plan of the resource it wraps. `NodeGraphCoordinator.build` computes it; the first public call computes it lazily when the resource is used without a machine.

**Rationale**: the plan depends only on `@entities` and the entity relation metadata, so it can be computed before any call and cached; the lazy fallback keeps direct use of a resource (a unit test, a script) checked. Eager computation at build is where the spec puts it and lets a broken declaration fail with the model, not with the first request.

**Alternatives considered**: walking relations on every call — rejected on cost; computing the plan in the wrapper constructor — rejected because there is no wrapper object.

## The pool keeps the connection body, not the model

**Decision**: `PostgresPool` owns `dsn` or a ready pool and the `open`/`close`/`acquire`/`release` body of today's `PostgresDataSource`; it is a plain class with no `@meta`, no kind and no graph node. `PostgresStorage` takes `pool=` or `connection_params=` and keeps the transaction.

**Rationale**: the data source was introduced because several resources shared a physical store; after this change the resource *is* the store, so the connection machinery survives as an object the application assembles, and the model stops seeing it. Exactly one of the two arguments mirrors the data source's own rule and gives one clear refusal.

**Alternatives considered**: keeping a resource-less "connection factory" name — rejected: the issue names the pool; one connection per resource always — rejected: a service assembles a pool once, a script needs a connection per call.

## `@entities` is its own intent

**Decision**: a new decorator and resolver under `src/intents/entities/`, mirroring `@entity` and `@meta`, writing `_entities_info`.

**Rationale**: the repository's declarations are intents with their own scratch key and resolver; a resource's entities are a declaration of their own, not metadata, and `@meta` changes meaning (no domain) at the same time. Keeping it separate keeps each resolver single-purpose.

**Alternatives considered**: an attribute on the class — rejected: no validation, and inconsistent with the other declarations; extending `@meta` — rejected: two unrelated concerns in one decorator.

## Protocol 2.0 comes from gnomon, not from this repository

**Decision**: copy `2.0.json` from gnomon's merge commit of #66 (`5d9dac89617aef08ea508988ce9106c1d82d8285`), pin `graph-builder` to that commit for the write and the check, and update the schema-copy test with the version.

**Rationale**: the graph schema belongs to the Open Gnomon Protocol; AOA copies it and tests the copy. The commit is the one the issue names, and CI already takes `graph-builder` from a gnomon commit.

**Alternatives considered**: waiting for a Maxitor release — rejected: the issue names the commit.

## The demo's databases live together

**Decision**: merged resources go to `packages/aoa-demo/src/aoa/demo/model/databases/`, one module per database; `ShopDatabaseStorage` merges the store, support and inventory resources that share one database today.

**Rationale**: after this change a resource belongs to no domain, so a package named after a domain no longer owns it; one module per database keeps the demo's layout honest and makes the merge visible. Other storages that keep their database stay where they are unless their module is named after a data source.

**Alternatives considered**: keeping the merged class in the store package — rejected: it would make one domain's package own a database three domains use.

## The cost is guarded, not benchmarked in microseconds

**Decision**: the 5% figure is measured by a benchmark marked `benchmark`, which the closing check run leaves out; the regular tests guard only a loose upper bound on the demo's entities, so a regression is caught and noise is not. Neither asserts 0.2 µs.

**Rationale**: wall-clock microseconds on a build machine are noisy, and the measured ratio sits near the line — 2.8% for the planned walk and 4.6% for a plain one — so a hard 5% assertion on a shared, parallel CI machine would fail at random.

**Alternatives considered**: a strict 0.2 µs assertion — rejected as flaky.

## Which methods carry the check

**Decision**: the plain functions, coroutine functions and async generators of a resource class body whose names do not start with `_`; class methods, static methods and properties are left alone.

**Rationale**: those are the entry points an action calls and the ones that return data. `get_wrapper_class` became a class method in #486 and returns a class, not data; wrapping descriptors would change how they bind. A plain generator, and a plain function that returns an awaitable, hand back an object the wrapper cannot see through without running it, so they are stated as unchecked rather than half-checked.

**Alternatives considered**: wrapping every callable attribute — rejected: it breaks descriptors and adds cost to methods that return no data.
