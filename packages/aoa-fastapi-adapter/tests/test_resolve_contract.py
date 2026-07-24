# tests/test_resolve_contract.py
"""
Contract test: one fixture, read by both Python and TypeScript (chapter 5, "Случай 2").

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``contracts/fixtures/resolve_response_basic.json`` is a real ``ResolveResponse``.
This test parses it with the real pydantic model; the companion TypeScript example
(``examples/step_27_ui_permissions_codegen/04_contract_fixture_resolve_response.ts``)
parses the identical file with the generated ``ResolveResponseSchema`` (zod). If
someone changes the shape of ``AllowedVerdict``/``FailSecurityVerdict``/
``FailErrorVerdict`` on one side and not the other, one of the two goes red --
this is the Python half of that guarantee, not a test of endpoint-set drift
(that's runtime ``UNKNOWN_ENDPOINT`` plus ``aoa-codegen --check``, not a fixture).
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import AllowedVerdict, FailErrorVerdict, FailSecurityVerdict
from aoa.fastapi.permissions_schema import ResolveResponse

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "resolve_response_basic.json"


def test_fixture_exists_and_is_valid_json() -> None:
    assert FIXTURE_PATH.is_file(), f"missing fixture: {FIXTURE_PATH}"
    json.loads(FIXTURE_PATH.read_text())


def test_fixture_matches_python_schema() -> None:
    fixture = FIXTURE_PATH.read_text()
    resp = ResolveResponse.model_validate_json(fixture)

    assert resp.version == 1
    assert len(resp.results) == 2
    assert isinstance(resp.results[0], AllowedVerdict)
    assert isinstance(resp.results[1], FailSecurityVerdict)
    assert resp.results[1].reason == "only the order owner can cancel"


def test_round_trips_all_three_verdict_kinds() -> None:
    """Not just this one fixture -- every BaseVerdict subclass, serialized then
    parsed back, must come back as itself (dispatch by kind, not the abstract base).
    """
    original = ResolveResponse(
        version=1,
        results=[AllowedVerdict(), FailSecurityVerdict(reason="no"), FailErrorVerdict(reason="UNKNOWN_ENDPOINT")],
    )
    reparsed = ResolveResponse.model_validate_json(original.model_dump_json())

    assert isinstance(reparsed.results[0], AllowedVerdict)
    assert isinstance(reparsed.results[1], FailSecurityVerdict)
    assert reparsed.results[1].reason == "no"
    assert isinstance(reparsed.results[2], FailErrorVerdict)
    assert reparsed.results[2].reason == "UNKNOWN_ENDPOINT"


def test_unrecognized_kind_still_raises() -> None:
    """The dispatcher must not accidentally turn an invalid kind into a silent
    pass-through -- an unrecognized kind falls through to normal validation
    against the abstract BaseVerdict, which rejects it.
    """
    with pytest.raises(ValidationError):
        ResolveResponse.model_validate({"version": 1, "results": [{"kind": "SomethingElse"}]})


def test_missing_required_reason_still_raises() -> None:
    """The dispatcher constructs the real subclass -- it must not bypass that
    subclass's own field validation (reason mandatory and non-empty)."""
    with pytest.raises(ValidationError):
        ResolveResponse.model_validate({"version": 1, "results": [{"kind": "FailSecurityVerdict"}]})
