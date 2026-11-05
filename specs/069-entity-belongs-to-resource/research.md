# Research: An entity belongs to one resource

Measured on `main` at `fea32db3c`.

## R1. Where the entity's domain is read

- **Decision**: `@entity` stores `resource`; `EntityIntentResolver.resolve_domain_type` reads the domain from the resource through `MetaIntentResolver.resolve_domain_type`. `resolve_domain_optional` goes: an entity always has a domain now.
- **Rationale**: the only reader of an entity's domain in `src` is `DomainGraphEdge.from_entity_declared_host` (through `resolve_domain_type`). Nothing in the adapters reads `_entity_info["domain"]`; `aoa-mcp-adapter` builds `node["domain"]` from the graph. Changing the resolver changes every reader at once.
- **Alternatives**: copying the resource's domain into `_entity_info["domain"]` at decoration — refused: it would be a second source, which spec FR-004 forbids.

## R2. What the decorator can check

- **Decision**: at class definition `@entity` refuses: no `resource`; a value that is not a class (a tuple included, with its own message naming every member); a class that is not a `BaseResource` subclass; a class excluded from the graph model (`BaseResource`, `BaseStorage`, `BaseGateway`, `BaseController` and any other `exclude_graph_model` host — its node never exists, so the edge could never be written); a resource with no usable `@meta` domain. All raise `EntityDecoratorError` naming the entity.
- **Rationale**: the resource class is always defined before the entity that names it, so its `@meta` is already applied. `excluded_from_graph_model` reads the class's own `__dict__`, so a concrete subclass of an excluded kind passes.
- **Problem found**: the decorator's validators run before `decorator(cls)` receives the class, so they cannot name the entity. The resource checks move inside `decorator(cls)`.
- `domain=` is simply removed from the signature: Python raises `TypeError: entity() got an unexpected keyword argument 'domain'` (case 2.2).

## R3. Where the model build refuses a relation across resources

- **Decision**: a new validator, `graph/validators/entity_resource_validator.py`, `validate_entity_resources()`, run in `NodeGraphCoordinator.build` beside `validate_entity_inverses` (before nodes are gathered). For every loaded `@entity` class it reads `resolve_entity_fields(host)` and compares the host's resource with: every target of a relation field (association, aggregation, composition, a dictionary field — dictionaries use the same containers), the `inverse_entity` of an inverse side, every target of a specialization or generalization field; and, for every `Lifecycle[...]` field, the resource of every other entity using the same state type.
- **Rationale**: the three existing class-level validators (`entity_field`, `entity_inverse`, `entity_role_compatibility`) run at this point on the same `ResolvedEntityField` rows; one more pass in the same shape adds no new path. A relation names classes that may be defined later in the module, so the decorator cannot judge it.
- **Exception**: `EntityResourceError` (new, in `aoa.action_machine.exceptions`), message shape of case 2.4: `<Host>.<field> relates <Host> (<ResourceA>) to <Target> (<ResourceB>): a relation stays inside one resource.` For a state type: `<StateType> is the state type of <HostA>.<field> (<ResourceA>) and <HostB>.<field> (<ResourceB>): a lifecycle stays inside one resource.`
- **Order**: the pass runs after `validate_entity_fields` (so a field without a form is named first) and before the inverse pass.

## R4. The graph edge and the graph build check

- **Decision**: `graph/edges/entity_resource_graph_edge.py`, `EntityResourceGraphEdge(AggregationGraphEdge)`, `edge_name="entity_resource"`, `is_dag=True`, empty `properties`, default edge id `<entity>|entity_resource|<resource>`. `EntityGraphNode` gets a `resource` field and lists the edge in `get_all_edges`.
- **Decision**: `NodeGraphCoordinator.build` gets `_validate_entity_resource_edges(nodes)` after wiring: every `Entity` node has exactly one `entity_resource` edge, and both ends of every `entity_relation`, `entity_specialization`, `parent_entity`, `entity_reference` and lifecycle-state link have the same resource; a failure raises `InvalidGraphError` naming the entity or entities and their resources. No graph is indexed or written on failure.
- **Rationale**: the node-level check reads the built nodes, not the classes; it catches what a custom inspector or a future edge could bring in past the class-level pass, which is what the issue asks of the graph build (2.5).
- **Resource node**: `ResourceGraphNodeInspector` already emits a node for every loaded `BaseResource` subclass that is not excluded, whether an action depends on it or not, so the edge target always exists once R2 refuses excluded classes.

## R5. Protocol 1.6

- **Decision**: `graph_json_schema.json` becomes gnomon's `packages/open-gnomon-protocol/graph/1.6.json` byte for byte (gnomon `main` at `2d6159df`, PR #47); `to_json` writes `"schema_version": "1.6"`; `tests/scripts/test_schema_copies.py` pins 1.6's `$id` and SHA-256; docstrings saying 1.5 move to 1.6; tests that assert `"1.5"` move with it.

## R6. State types

- **Decision**: a state type (`BaseStateEntity`, excluded from the graph model) gets no declaration. The class-level pass groups `Lifecycle[...]` fields by state type and refuses a group whose hosts have more than one resource. In the graph, state nodes are companions of their host entity node (ids prefixed with the host) and carry `lifecycle_class_id`; the node-level check groups state nodes by `lifecycle_class_id` and refuses a group whose hosts have different resources.

## R7. Moving every declaration

- **Decision**: a script in the session scratchpad (not committed) rewrites `@entity(..., domain=X)` to `@entity(..., resource=<X-store>)` and inserts, once per domain per file, a storage resource right after the domain class (or after the imports when the domain is imported):

  ```python
  @meta(description="Stores the shop model", domain=ShopDomain)
  class ShopStorage(BaseStorage):
      """Hold the shop model's entities."""
  ```

  An abstract storage is enough: the entity needs the class, never an instance. Files where a relation would then cross resources are fixed by hand.
- **Counts** (lines starting with `@entity(`): 373 in 61 files of `aoa-action-machine/tests`, 18 in the adapters' tests, 364 in 115 files of `examples/`, 213 in the demo, 52 in 14 pages of `docs/`, 4 in `README.md`. `domain=` written on its own line inside a multi-line `@entity(` is handled by the same script.

## R8. The demo

- **Decision** (clarification 3: the demo exists for volume): each of the 13 domains without a resource gets `<Domain>Storage`; `CurrencyEnumEntity` moves into `aoa/demo/model/billing/` and is stored by `BillingWarehouse`, `DictionariesDomain` goes; the 23 other cross-domain associations are removed; in Store, Billing, Messaging and Catalog the entities are spread by meaning (session/cart → `StorefrontSessionCache`, payment events → `PaymentGatewayResource`, dead letters → `MessagingDeadLetterStore`, search projections → `CatalogSearchSidecar`, the rest to the domain's database); any relation that then crosses resources is removed or its entity moves; `CatalogDenseLifecycle` is split per resource. What moved is listed in the demo phase's commit message.

## R9. Versions

- **Decision**: levels touched — root `version.toml`, `packages/aoa-action-machine` (breaking: `@entity` signature → major), `packages/aoa-demo`, and every adapter package whose tests change (`aoa-fastapi-adapter`, `aoa-mcp-adapter`, `aoa-langgraph`, `aoa-ocel`) — raised as `version-gate` requires; the exact list comes from `version-gate` on the branch.
