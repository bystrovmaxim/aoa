# tests/test_resolve_contract.py
"""
Contract test, Python half: every fixture in ``contracts/fixtures/`` (chapter 12, #144).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each file in ``contracts/fixtures/`` is a complete ``POST /permissions/resolve``
response body, read by BOTH halves of the system: here with the real pydantic
model, and in ``packages/aoa-client-js/src/codegen/resolve-contract.test.ts``
with the generated zod schema. If someone changes the shape of
``AllowedVerdict``/``FailSecurityVerdict``/``FailErrorVerdict`` on one side and
not the other, one of the two goes red.

This is not a test of endpoint-set drift (that is runtime ``UNKNOWN_ENDPOINT``
plus ``aoa-codegen --check``) -- only of the response *shape*.

═══════════════════════════════════════════════════════════════════════════════
HOW THE FIXTURES ARE SPLIT
═══════════════════════════════════════════════════════════════════════════════

By filename, because a convention both languages can apply is the only thing
that keeps the two halves testing the same partition of the same directory:
``resolve_response_invalid_*.json`` must be REJECTED, every other
``resolve_response_*.json`` must PARSE. See ``contracts/fixtures/README.md``.

Discovery is guarded (:func:`test_discovery_found_both_groups`): a glob-driven
suite that silently finds zero files passes vacuously, which is the one failure
mode a data-driven test has and a hand-written one does not.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from aoa.action_machine.intents.access_control import AllowedVerdict, FailErrorVerdict, FailSecurityVerdict
from aoa.fastapi.permissions_schema import ResolveResponse

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"

VALID_FIXTURES = sorted(p for p in FIXTURE_DIR.glob("resolve_response_*.json") if "_invalid_" not in p.name)
INVALID_FIXTURES = sorted(FIXTURE_DIR.glob("resolve_response_invalid_*.json"))


def _ids(paths: list[Path]) -> list[str]:
    return [p.stem for p in paths]


def test_discovery_found_both_groups() -> None:
    """Without this, renaming the fixtures to something the glob misses would turn
    every parametrized test below into zero test cases -- a green suite that
    checks nothing. The exact counts are deliberately not pinned (adding a
    fixture should not require editing this file); only "both groups are
    non-empty, and the valid ones outnumber a single file" is asserted.
    """
    assert FIXTURE_DIR.is_dir(), f"missing fixture directory: {FIXTURE_DIR}"
    assert len(VALID_FIXTURES) >= 2, f"expected several valid fixtures, found {_ids(VALID_FIXTURES)}"
    assert len(INVALID_FIXTURES) >= 2, f"expected several invalid fixtures, found {_ids(INVALID_FIXTURES)}"


@pytest.mark.parametrize("fixture", VALID_FIXTURES, ids=_ids(VALID_FIXTURES))
def test_valid_fixture_is_valid_json(fixture: Path) -> None:
    json.loads(fixture.read_text())


@pytest.mark.parametrize("fixture", VALID_FIXTURES, ids=_ids(VALID_FIXTURES))
def test_valid_fixture_parses_and_round_trips_without_loss(fixture: Path) -> None:
    """Parse, then serialize back, then compare against the file's own JSON.

    Plain "it parses" is too weak: pydantic would happily accept a file whose
    fields it silently dropped. Comparing the re-serialized form against the
    original catches both directions of loss -- a field the model ignored, and a
    field the model invented.
    """
    raw = fixture.read_text()
    parsed = ResolveResponse.model_validate_json(raw)

    assert parsed.model_dump(mode="json") == json.loads(raw)


# Which rule each broken fixture violates, as pydantic reports it: (error type,
# location). Asserting only "it raised" is what let the whole set rot -- every one
# of the five could be replaced with unrelated garbage (even invalid JSON) and both
# halves of the contract stayed green, because *something* was still rejected. The
# fixture then no longer tests what its name claims, and nothing says so.
#
# Type AND location together, because type alone does not separate them: "no reason
# at all" and "unrecognized kind" both surface as value_error, differing only in
# whether the failure is attributed to the whole list or to element 0.
EXPECTED_REJECTION: dict[str, tuple[str, list[object]]] = {
    "resolve_response_invalid_missing_reason": ("value_error", ["results"]),
    "resolve_response_invalid_empty_reason": ("string_too_short", ["results", "reason"]),
    "resolve_response_invalid_unknown_kind": ("value_error", ["results"]),
    "resolve_response_invalid_extra_field": ("extra_forbidden", ["results", "cachedUntil"]),
    "resolve_response_invalid_allowed_with_reason": ("extra_forbidden", ["results", "reason"]),
}


def test_every_invalid_fixture_has_a_declared_expected_rejection() -> None:
    """The table above must cover the directory, or a newly added broken fixture
    would silently fall back to no assertion at all about WHY it fails.
    """
    assert {p.stem for p in INVALID_FIXTURES} == set(EXPECTED_REJECTION)


@pytest.mark.parametrize("fixture", INVALID_FIXTURES, ids=_ids(INVALID_FIXTURES))
def test_invalid_fixture_is_rejected_for_the_rule_it_actually_violates(fixture: Path) -> None:
    """A parser that accepts everything is not a parser -- and a test that only
    checks "it raised" is barely better. Each of these files violates exactly one
    rule (see contracts/fixtures/README.md), and the assertion names that rule, so
    a fixture whose content drifts away from its filename fails instead of quietly
    passing on some unrelated error.
    """
    expected_type, expected_loc = EXPECTED_REJECTION[fixture.stem]

    with pytest.raises(ValidationError) as caught:
        ResolveResponse.model_validate_json(fixture.read_text())

    first = caught.value.errors()[0]
    assert (first["type"], list(first["loc"])) == (expected_type, expected_loc)


# ── Per-fixture meaning ───────────────────────────────────────────────────────
# The parametrized tests above prove the whole set is well-formed. These prove
# that specific files still mean what their names claim -- a fixture whose
# content drifted would still parse, and the generic tests would not notice.


def test_basic_fixture_still_carries_an_allow_and_a_role_denial() -> None:
    parsed = ResolveResponse.model_validate_json((FIXTURE_DIR / "resolve_response_basic.json").read_text())

    assert parsed.version == 1
    assert len(parsed.results) == 2
    assert isinstance(parsed.results[0], AllowedVerdict)
    assert isinstance(parsed.results[1], FailSecurityVerdict)
    assert parsed.results[1].reason == "only the order owner can cancel"


def test_object_forbidden_fixture_answers_missing_and_foreign_byte_identically() -> None:
    """Oracle safety, asserted on the parsed objects rather than on the file text.

    "No such object" and "object belongs to someone else" are the two questions
    in this fixture, and the assertion is equality of the WHOLE verdict, not merely
    of its class.

    Being precise about what this can and cannot catch, since the two elements are
    written identically in the file and a parser will not invent a difference: this
    guards the FIXTURE, not the server. It fails when someone edits the file so the
    two stop matching -- which is exactly how the documented invariant would be
    weakened by hand. That the SERVER answers identically for a missing and a
    foreign object is a different claim, tested against a real app in
    test_fastapi_permissions_resolve.py's TestObjectLevelCodesOverHttp.
    """
    parsed = ResolveResponse.model_validate_json((FIXTURE_DIR / "resolve_response_object_forbidden.json").read_text())

    missing, foreign = parsed.results
    assert isinstance(missing, FailSecurityVerdict)
    assert missing.model_dump() == foreign.model_dump()
    assert missing.reason == "FORBIDDEN_OBJECT"


def test_all_kinds_mixed_fixture_carries_every_class_in_one_response() -> None:
    """One response can mix all three outcome classes, and position is what ties
    an answer to its question -- there is no id, no echo of the operation.
    """
    parsed = ResolveResponse.model_validate_json((FIXTURE_DIR / "resolve_response_all_kinds_mixed.json").read_text())

    assert [type(result) for result in parsed.results] == [
        AllowedVerdict,
        FailSecurityVerdict,
        FailErrorVerdict,
        AllowedVerdict,
    ]


@pytest.mark.parametrize(
    ("fixture_name", "expected_reason"),
    [
        ("resolve_response_unknown_endpoint.json", "UNKNOWN_ENDPOINT"),
        ("resolve_response_evaluation_failed.json", "EVALUATION_FAILED"),
    ],
)
def test_check_error_fixtures_are_errors_and_not_denials(fixture_name: str, expected_reason: str) -> None:
    """Both reasons arrive as FailErrorVerdict, never FailSecurityVerdict. The
    distinction is the whole reason the third class exists: a client that renders
    "not allowed" for these is lying about a check that never ran.
    """
    parsed = ResolveResponse.model_validate_json((FIXTURE_DIR / fixture_name).read_text())
    errors = [result for result in parsed.results if isinstance(result, FailErrorVerdict)]

    assert [error.reason for error in errors] == [expected_reason]
    assert not any(isinstance(result, FailSecurityVerdict) for result in parsed.results)


# ── The other direction: TypeScript builds, Python reads ─────────────────────
#
# Every fixture travels Python -> TypeScript. Each valid one is asserted
# byte-equivalent to what this very model would emit (the round-trip test above),
# and the TypeScript half then parses it -- so that direction genuinely is covered,
# contrary to how it is sometimes described. What was NOT covered is the reverse: a
# response shaped the way TYPESCRIPT believes it should be shaped had never been
# handed to pydantic. A fixture cannot close this, by construction: it is one file
# read by both, so it can only ever contain a shape both sides already agree on.

EMITTER = FIXTURE_DIR.parent / "emit_response_from_ts.ts"


def test_a_response_built_by_typescript_is_accepted_by_the_python_model() -> None:
    """Spawn the TypeScript emitter and feed its stdout straight to the model.

    Skipped rather than failed when node is absent: this is the one test in the
    Python suite that needs the other toolchain, and a machine without it should
    not be told the contract is broken. ``scripts/run_checks_with_log.sh`` installs
    node before pytest runs, so the normal flow always exercises it.
    """
    if shutil.which("node") is None:
        pytest.skip("node is not installed -- the cross-language direction cannot run here")
    assert EMITTER.is_file(), f"missing emitter: {EMITTER}"

    emitted = subprocess.run(
        ["node", "--experimental-strip-types", str(EMITTER)],
        capture_output=True,
        text=True,
        check=True,
        cwd=EMITTER.parent.parent,
    ).stdout

    parsed = ResolveResponse.model_validate_json(emitted)

    # All three classes, so a disagreement about any one of them is caught rather
    # than only whichever happened to come first.
    assert [type(result).__name__ for result in parsed.results] == [
        "AllowedVerdict",
        "FailSecurityVerdict",
        "FailErrorVerdict",
    ]


@pytest.mark.parametrize("bad_version", ["1", True, 1.0])
def test_version_is_strict_so_both_halves_agree_on_it(bad_version: object) -> None:
    """The live divergence this phase existed to close.

    pydantic used to coerce "1", true and 1.0 all to 1 while the generated zod
    validator rejected them, so the two halves disagreed about real responses and
    no fixture could reveal it. ResolveResponse.version is now strict; the two
    sides accept and reject the same set.
    """
    with pytest.raises(ValidationError):
        ResolveResponse.model_validate({"version": bad_version, "results": []})


# ── Shape guarantees beyond the files ─────────────────────────────────────────


def test_round_trips_all_three_verdict_kinds_constructed_in_python() -> None:
    """The fixtures cover parsing files written by hand; this covers the opposite
    direction -- a response this code CONSTRUCTS, serialized and parsed back, must
    come back as the same concrete subclasses (dispatch by kind, not the abstract
    base).
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


def test_an_undeclared_field_on_the_envelope_itself_is_rejected_too() -> None:
    """Coverage asymmetry the fixtures cannot cover: every broken fixture puts its
    extra field inside a verdict, so nothing checked the response object itself.
    The TypeScript half already asserted this; the Python half did not.
    """
    with pytest.raises(ValidationError):
        ResolveResponse.model_validate({"version": 1, "results": [], "serverTime": 123})


def test_unrecognized_kind_still_raises() -> None:
    """The dispatcher must not turn an invalid kind into a silent pass-through. It
    holds the only list of kinds that exist on the wire, so it rejects the unknown
    one itself, naming both the offending index and the kind.
    """
    with pytest.raises(ValidationError) as caught:
        ResolveResponse.model_validate({"version": 1, "results": [{"kind": "SomethingElse"}]})

    assert "results[0]" in str(caught.value)
    assert "SomethingElse" in str(caught.value)


def test_missing_required_reason_still_raises() -> None:
    """The dispatcher constructs the real subclass -- it must not bypass that
    subclass's own field validation (reason mandatory and non-empty)."""
    with pytest.raises(ValidationError):
        ResolveResponse.model_validate({"version": 1, "results": [{"kind": "FailSecurityVerdict"}]})
