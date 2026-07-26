"""
examples/step_27_ui_permissions_resolve/11_contract_fixture_and_its_broken_twin.py

What a contract fixture is, and what a RED contract test looks like.

A fixture set made only of valid files proves nothing: a parser that accepts
everything would pass it completely. Every valid fixture therefore has broken
twins -- files violating exactly one rule each -- and both halves of the system,
Python here and TypeScript in `resolve-contract.test.ts`, must REFUSE them.

Run: uv run python examples/step_27_ui_permissions_resolve/11_contract_fixture_and_its_broken_twin.py
"""

import json
from pathlib import Path

from pydantic import ValidationError

from aoa.action_machine.intents.access_control import FailErrorVerdict, FailSecurityVerdict
from aoa.fastapi.permissions_schema import ResolveResponse

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text()


# ── 1. A valid fixture parses, and round-trips without loss ──────────────────
#
# "It parsed" is too weak on its own: pydantic will happily accept a file whose
# fields it silently dropped. Comparing the re-serialized form against the file
# catches loss in both directions -- a field the model ignored, and a field the
# model invented.
print("── valid: resolve_response_all_kinds_mixed.json ──")
raw = _load("resolve_response_all_kinds_mixed.json")
parsed = ResolveResponse.model_validate_json(raw)
print("  classes:   ", [type(result).__name__ for result in parsed.results])
print("  round-trip:", "identical" if parsed.model_dump(mode="json") == json.loads(raw) else "LOST DATA")


# ── 2. Oracle safety, encoded in the data itself ─────────────────────────────
#
# Two questions -- one about an object that does not exist, one about an object
# belonging to someone else -- and one answer. If those two ever stop matching,
# anyone can learn which IDs exist for other users just by reading the difference.
print("\n── valid: resolve_response_object_forbidden.json ──")
missing, foreign = ResolveResponse.model_validate_json(_load("resolve_response_object_forbidden.json")).results
print("  'no such object': ", missing.model_dump())
print("  'someone else's': ", foreign.model_dump())
print("  indistinguishable:", missing.model_dump() == foreign.model_dump())


# ── 3. A failure is not a denial ─────────────────────────────────────────────
print("\n── valid: resolve_response_evaluation_failed.json ──")
crashed = ResolveResponse.model_validate_json(_load("resolve_response_evaluation_failed.json")).results[0]
print(f"  class:  {type(crashed).__name__}")
print(f"  denial? {isinstance(crashed, FailSecurityVerdict)}   check failed? {isinstance(crashed, FailErrorVerdict)}")


# ── 4. The broken twins -- what a red contract test actually looks like ──────
#
# Each of these violates exactly one rule. The error text below is what a
# developer sees when they change the wire shape on one side and forget the
# other; that message IS the value of the whole mechanism.
print("\n── broken twins: every one of these must be REFUSED ──")
for name, rule in [
    ("resolve_response_invalid_missing_reason.json", "a failure verdict with no reason at all"),
    ("resolve_response_invalid_empty_reason.json", "reason present but empty"),
    ("resolve_response_invalid_unknown_kind.json", "a kind outside the closed set of three"),
    ("resolve_response_invalid_extra_field.json", "a field nobody declared"),
    ("resolve_response_invalid_allowed_with_reason.json", "success carrying a reason -- it has no such field"),
]:
    try:
        ResolveResponse.model_validate_json(_load(name))
        print(f"  {name}\n    ACCEPTED — the check is broken, not the fixture")
    except ValidationError as exc:
        first = exc.errors()[0]
        print(f"  {rule}\n    refused: {first['type']} at {list(first['loc'])}")
