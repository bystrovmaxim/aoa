# SC-001 search — recorded result

**Date**: 2026-10-24
**Pattern**: `grant(`, `Grant`, `guard=`, `guard_reason`, `Gate.WHEN`, `Gate.GUARD`, and
`WHEN`/`GUARD` as gate values, over source, tests, examples and documentation.

## Exempt places (migration and verification material)

- `check_roles_decorator.py` — the refusal message that names the removed keywords to refuse them clearly.
- `test_check_roles_removed_mechanism.py` — the test that imports `grant`/`Grant` to assert `ImportError`, and passes the removed keywords to assert the refusal.
- the tutorial's migration section and `docs/CHANGELOG.md` (the changelog article is written last).

## Result

No leftover declaration, working import or teaching instruction names the removed mechanism.

The only hits outside the exempt places are:

- `test_action_graph_node.py` and `test_access_cascade_shapes.py` — `assert "guard_reason" not in node.properties`; they name the removed key only to assert its absence.
- `action_schema_intent_resolver.py:108` — `recursive_guard=frozenset()`; the word is an unrelated variable name, not the removed API.

No page outside the migration material says "four steps" or "five words".
