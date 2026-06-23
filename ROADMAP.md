# Roadmap — Q3 2026

## Goal for the quarter

Address key infrastructure needs: observability, security, testability. Prepare AOA for the first stable release (1.0.0).

---

- [X] **(High priority)** Develop `OpenTelemetryPlugin` that subscribes to Action lifecycle events (spans for each aspect)

- [ ] **(High priority)** Add `Channel.client` to `box.info/warning/critical` for end‑user notifications

- [X] **(High priority)** Make `ConsoleLogger` colors configurable per severity level (e.g., `info` currently white, invisible on white background in Colab) – allow setting a default dark color for `info`

- [ ] **(High priority)** Implement 4 authentication methods: HTTP Basic Auth, Bearer Token (JWT), API Key, OAuth2 (Google/GitHub/Keycloak)

- [ ] **(High priority)** Add a `condition: Callable[[AuthSession, Params], bool]` parameter to `@check_roles` for flexible authorization (lambda evaluated after role checks)

- [x] **Rename `NoneRole` → `GuestRole`** — `NoneRole` removed; `GuestRole` is the canonical name.

- [ ] **(High priority)** Allow compensation to be referenced by function name (as an object) instead of a string — improve type safety and refactoring

- [ ] **(High priority)** Enhance `TestBench`: return an `ExecutionTrace` containing all intermediate `state` snapshots, the list of executed aspects, and compensations called

- [X] **(High priority)** Initialize `GraphCoordinator` by default in `ActionProductMachine` (remove the need to pass it explicitly in simple cases)

- [X] **(High priority)** Initialize `ConsoleLogger` by default in `ActionProductMachine` — out-of-the-box logging without explicit setup

- [X] **(High priority)** Initialize in-memory cache adapter by default in `ActionProductMachine` — caching available without explicit configuration

- [X] **(High priority)** Tag-based cache invalidation: `on_cache_write` returns `list[CacheTag] | None` (tags indexed alongside the entry); new `on_cache_invalidate` hook (called after every clean pipeline) returns `list[CacheTag] | None` — wildcard-aware matchers (`None` field = wildcard); `CacheCoordinator` gains a tag index and `evict_by_tags`; invalidation happens before write. `CacheKeyMixin` removed — produced un-invalidatable entries.

- [ ] **(High priority)** `Result` fields are emitted to OTel logs without sensitivity filtering. `OpenTelemetryPlugin._result_attributes` serializes every result field (summary / `@on_error` / finish) verbatim (length-truncated only); `opaque` is not applied to results and `@sensitive` masking from the logging layer is ignored, so tokens/PII in `Result` leak into the log backend. Decide and implement one of: an `include_result_fields: bool = False` safe default, extending the `opaque` / `@sensitive` mechanism to the result projection, or an explicit documented limitation.

- [ ] **(Medium priority)** LangGraph integration: add `LangGraphNodeMixin` that injects `__call__(self, agentstate, config)` into any Action, making it usable as a LangGraph node directly. Machine and AOA context are passed via `config["configurable"]`; Params fields are extracted from `agentstate` (exception if fields missing). Preserves all Action guarantees (roles, compensations, error handlers) inside the LangGraph graph. Ship as `aoa-action-machine[langgraph]` optional extra.

- [ ] **(Research)** Supervisor Actions — living cell model: a `SupervisorAction` is a special Action whose body is typically an LLM/AI agent. It receives a stream of machine events (via the plugin system) — e.g. error counts per Action, business-operation anomalies, throughput signals — and can trigger machine restructuring or launch arbitrary activity in response. Plugins act as receptors (sensors); the supervisor acts as the nucleus that interprets signals and decides. This enables a self-regulating machine: the plugin layer observes, the supervisor reasons, the machine adapts. Unlike infrastructure-level self-healing (Kubernetes, circuit breakers), the supervisor reasons in business-domain terms: e.g. "`CreateOrderAction` failed 47 times in the last 5 minutes — root cause: `InventoryCheckAction` returning timeout" — and can respond with domain-aware decisions, not just infrastructure restarts. Requires: a signal-routing protocol from plugins to supervisor, a safe API for supervisor-initiated machine reconfiguration, and isolation guarantees so a supervisor cannot violate Action contracts.

- [ ] **(Research)** Add an `environment` block to `Context` as an explicit environment port. Define environment values declaratively on the `Context` class, for example with decorators that register providers instead of fixed values: `@environment("feature_flag", lambda: read_flag(...), cache="request")`. `@context_requires` would then expose these values to Actions as another declared context slice. The key idea is lazy reading: when an Action accesses the environment field, the provider is called, so updated environment values can be observed without restarting the machine; optional per-request caching can keep one call stable within a request. Research questions: provider API shape, cache scopes (`none`, `request`, `ttl`), type validation, masking/sensitivity rules, observability of environment reads, and guarantees that environment access remains explicit rather than becoming a hidden global.

*Last updated: June 19, 2026*