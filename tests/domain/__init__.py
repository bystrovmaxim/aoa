# tests/domain/__init__.py
"""
Unit tests for the domain layer (`action_machine.domain`).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each `test_*.py` module targets one slice of domain behavior: entities,
lifecycle FSMs, relation markers and containers, hydration (`build()`),
`make()` helpers, and shared schema utilities used by entities.

═══════════════════════════════════════════════════════════════════════════════
SCOPE
═══════════════════════════════════════════════════════════════════════════════

In scope: behavior and contracts of types under `src/action_machine/domain/`
(and `BaseSchema` where entities rely on it).

Out of scope: the shared **test domain model** (`tests/scenarios/domain_model/`) — that
package is integration-style fixtures for Actions; it is tested indirectly
and via its own consumers, not re-documented here.

═══════════════════════════════════════════════════════════════════════════════
TERMINOLOGY
═══════════════════════════════════════════════════════════════════════════════

Uses the same words as production code: **entity** (`@entity`, `BaseEntity`),
**lifecycle** (fluent template + instance state), **relation** (`Rel`,
`Inverse` / `NoInverse`, association containers), **hydration** (`build()` from
plain data).
"""
