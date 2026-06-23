# Roadmap — Q3 2026

## Goal for the quarter

Address key infrastructure needs: observability, security, testability. Prepare AOA for the first stable release (1.0.0).

---

- [X] **(High priority)** Develop `OpenTelemetryPlugin` that subscribes to Action lifecycle events (spans for each aspect)

- [ ] **(High priority)** Add `Channel.client` to `box.info/warning/critical` for end‑user notifications

- [X] **(High priority)** Make `ConsoleLogger` colors configurable per severity level (e.g., `info` currently white, invisible on white background in Colab) – allow setting a default dark color for `info`

- [ ] **(High priority)** Implement 4 authentication methods: HTTP Basic Auth, Bearer Token (JWT), API Key, OAuth2 (Google/GitHub/Keycloak)

- [ ] **(High priority)** Add a `condition: Callable[[AuthSession, Params], bool]` parameter to `@check_roles` for flexible authorization (lambda evaluated after role checks)

- [X] **Rename `NoneRole` → `GuestRole`** — `NoneRole` removed; `GuestRole` is the canonical name.

- [ ] **(High priority)** Allow compensation to be referenced by function name (as an object) instead of a string — improve type safety and refactoring

- [ ] **(High priority)** Enhance `TestBench`: return an `ExecutionTrace` containing all intermediate `state` snapshots, the list of executed aspects, and compensations called

- [X] **(High priority)** Initialize `GraphCoordinator` by default in `ActionProductMachine` (remove the need to pass it explicitly in simple cases)

- [X] **(High priority)** Initialize `ConsoleLogger` by default in `ActionProductMachine` — out-of-the-box logging without explicit setup

- [X] **(High priority)** Initialize in-memory cache adapter by default in `ActionProductMachine` — caching available without explicit configuration

- [X] **(High priority)** Tag-based cache invalidation: `on_cache_write` returns `list[CacheTag] | None` (tags indexed alongside the entry); new `on_cache_invalidate` hook (called after every clean pipeline) returns `list[CacheTag] | None` — wildcard-aware matchers (`None` field = wildcard); `CacheCoordinator` gains a tag index and `evict_by_tags`; invalidation happens before write. `CacheKeyMixin` removed — produced un-invalidatable entries.

- [X] **(Medium priority)** LangGraph adapter (`aoa-langgraph-adapter`): fluent `LangGraphAdapter` that registers AOA Actions as LangGraph nodes via `.node()`, `.edge()`, `.conditional_edge()`, `.route()`, `.start()`, `.compile()`. Plain async functions supported alongside Actions (`.node(fn, name=...)`). Connection pool auto-filtered per Action by `@connection` declarations; missing connections raise `MissingConnectionError` at `.compile()`. Unregistered node in an edge call raises `UnregisteredNodeError` immediately. `.compile()` returns a standard LangGraph `CompiledGraph`; `.build_graph()` returns `StateGraph` for native LangGraph continuation. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))

- [ ] **(Research)** Supervisor Actions — living cell model: a `SupervisorAction` is a special Action whose body is typically an LLM/AI agent. It receives a stream of machine events (via the plugin system) — e.g. error counts per Action, business-operation anomalies, throughput signals — and can trigger machine restructuring or launch arbitrary activity in response. Plugins act as receptors (sensors); the supervisor acts as the nucleus that interprets signals and decides. This enables a self-regulating machine: the plugin layer observes, the supervisor reasons, the machine adapts. Unlike infrastructure-level self-healing (Kubernetes, circuit breakers), the supervisor reasons in business-domain terms: e.g. "`CreateOrderAction` failed 47 times in the last 5 minutes — root cause: `InventoryCheckAction` returning timeout" — and can respond with domain-aware decisions, not just infrastructure restarts. Requires: a signal-routing protocol from plugins to supervisor, a safe API for supervisor-initiated machine reconfiguration, and isolation guarantees so a supervisor cannot violate Action contracts.

- [X] **(High priority)** Declarative environment providers on `Context` via `@env` decorator. `@env(key, value_or_callable, ttl=0)` is a class decorator that registers an `EnvEntry` (frozen dataclass with mutable `_cache`) on the Context class; non-callables are auto-wrapped. `ttl=0` = cached forever, `ttl>0` = expires after N seconds (checked at next read via `time.monotonic()`), `ttl<0` = `ValueError`. Access via `@context_requires("env.key")` — `Context.resolve("env.key")` dispatches to `EnvEntry.get()`. `Context.model_config` gains `arbitrary_types_allowed=True`.

*Last updated: June 23, 2026*