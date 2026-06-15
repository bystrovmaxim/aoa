# Roadmap — Q3 2026

## Goal for the quarter

Address key infrastructure needs: observability, security, testability. Prepare AOA for the first stable release (1.0.0).

---

- [X] **(High priority)** Develop `OpenTelemetryPlugin` that subscribes to Action lifecycle events (spans for each aspect)

- [ ] **(High priority)** Add `Channel.client` to `box.info/warning/critical` for end‑user notifications

- [ ] **(High priority)** Make `ConsoleLogger` colors configurable per severity level (e.g., `info` currently white, invisible on white background in Colab) – allow setting a default dark color for `info`

- [ ] **(High priority)** Implement 4 authentication methods: HTTP Basic Auth, Bearer Token (JWT), API Key, OAuth2 (Google/GitHub/Keycloak)

- [ ] **(High priority)** Add a `condition: Callable[[AuthSession, Params], bool]` parameter to `@check_roles` for flexible authorization (lambda evaluated after role checks)

- [ ] **(High priority)** Rename `NoneRole` → `GuestRole` (keep the old name as a deprecated alias)

- [ ] **(High priority)** Allow compensation to be referenced by function name (as an object) instead of a string — improve type safety and refactoring

- [ ] **(High priority)** Enhance `TestBench`: return an `ExecutionTrace` containing all intermediate `state` snapshots, the list of executed aspects, and compensations called

- [ ] **(High priority)** Initialize `GraphCoordinator` by default in `ActionProductMachine` (remove the need to pass it explicitly in simple cases)

- [ ] **(High priority)** `Result` fields are emitted to OTel logs without sensitivity filtering. `OpenTelemetryPlugin._result_attributes` serializes every result field (summary / `@on_error` / finish) verbatim (length-truncated only); `opaque` is not applied to results and `@sensitive` masking from the logging layer is ignored, so tokens/PII in `Result` leak into the log backend. Decide and implement one of: an `include_result_fields: bool = False` safe default, extending the `opaque` / `@sensitive` mechanism to the result projection, or an explicit documented limitation.

*Last updated: June 15, 2026*