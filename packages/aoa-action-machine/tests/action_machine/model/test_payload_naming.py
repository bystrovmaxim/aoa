# packages/aoa-action-machine/tests/action_machine/model/test_payload_naming.py
"""PayloadNaming — parameter and result names are validated at declaration."""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.model import BaseParams, BaseResult


@pytest.mark.parametrize("base,suffix", [(BaseParams, "Params"), (BaseResult, "Result")])
def test_payload_names_accept_direct_and_indirect_descendants(base, suffix):
    """Permit abstract intermediate classes and correctly named descendants."""
    parent = type(f"Audit{suffix}", (base,), {})
    child = type(f"DetailedAudit{suffix}", (parent,), {})
    assert issubclass(child, base)


@pytest.mark.parametrize("base,suffix", [(BaseParams, "Params"), (BaseResult, "Result")])
@pytest.mark.parametrize("name", ["Audit", "ParamsAudit", "AuditResultSuffix", "Auditparams", "Auditresult"])
def test_payload_names_refuse_missing_or_misplaced_suffix(base, suffix, name):
    """Require the exact suffix at the end of every declared name."""
    with pytest.raises(NamingSuffixError) as caught:
        type(name, (base,), {})
    assert str(caught.value) == (
        f"Class '{name}' inherits {base.__name__} but lacks the '{suffix}' suffix. "
        f"Rename to '{name}{suffix}'."
    )


@pytest.mark.parametrize("base,suffix", [(BaseParams, "Params"), (BaseResult, "Result")])
def test_payload_names_check_indirect_descendants(base, suffix):
    """Keep enforcement when an intermediate payload is abstract."""
    parent = type(f"Audit{suffix}", (base,), {})
    with pytest.raises(NamingSuffixError, match="Class 'DetailedAudit'"):
        type("DetailedAudit", (parent,), {})


@pytest.mark.parametrize("base,suffix", [(BaseParams, "Params"), (BaseResult, "Result")])
def test_payload_naming_preserves_cooperative_subclass_hooks(base, suffix):
    """Forward class keywords to the next cooperative base."""
    observed = []

    class RegistrationMixin:
        """Consume an application registration keyword."""

        def __init_subclass__(cls, *, register=False, **kwargs):
            """Record registration without interfering with naming."""
            super().__init_subclass__(**kwargs)
            observed.append((cls, register))

    payload = type(f"Registered{suffix}", (base, RegistrationMixin), {}, register=True)
    assert observed == [(payload, True)]


@pytest.mark.parametrize("base,suffix", [(BaseParams, "Params"), (BaseResult, "Result")])
def test_payload_naming_preserves_pydantic_contract(base, suffix):
    """Keep fields, strict validation, JSON schema and frozen payloads."""
    from pydantic import ValidationError

    payload = type(f"Order{suffix}", (base,), {"__annotations__": {"quantity": int}})
    value = payload(quantity=3)
    assert value.model_dump() == {"quantity": 3}
    assert payload.model_json_schema()["properties"]["quantity"]["type"] == "integer"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        payload(quantity=3, extra=True)
    with pytest.raises(ValidationError, match="frozen_instance"):
        value.quantity = 4


def test_stub_payloads_have_only_new_public_names():
    """Expose renamed stubs through both public and direct imports."""
    import importlib.util

    import aoa.action_machine.model as model
    from aoa.action_machine.model.stub_params import StubParams
    from aoa.action_machine.model.stub_result import StubResult

    assert model.StubParams is StubParams
    assert model.StubResult is StubResult
    assert StubParams().model_dump() == StubResult().model_dump() == {}
    for old in ("ParamsStub", "ResultStub"):
        assert not hasattr(model, old)
    for old in ("params_stub", "result_stub"):
        assert importlib.util.find_spec(f"aoa.action_machine.model.{old}") is None
