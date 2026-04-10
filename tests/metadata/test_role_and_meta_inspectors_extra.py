"""Extra tests for role/meta inspectors with low coverage."""

from __future__ import annotations

from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.auth.role_gate_host_inspector import RoleGateHostInspector
from action_machine.core.meta_gate_host_inspector import MetaGateHostInspector
from action_machine.core.meta_gate_hosts import ActionMetaGateHost


class _RoleMissing(RoleGateHost):
    pass


class _RoleFilled(RoleGateHost):
    _role_info = {"spec": "admin"}


class _MetaMissing(ActionMetaGateHost):
    pass


class _MetaFilled(ActionMetaGateHost):
    _meta_info = {"description": "desc", "domain": None}


def test_role_gate_host_inspector_branches() -> None:
    assert RoleGateHostInspector.inspect(_RoleMissing) is None
    payload = RoleGateHostInspector.inspect(_RoleFilled)
    assert payload is not None
    assert payload.node_type == "role"
    assert dict(payload.node_meta)["spec"] == "admin"
    assert isinstance(RoleGateHostInspector._subclasses_recursive(), list)


def test_meta_gate_host_inspector_branches() -> None:
    assert MetaGateHostInspector.inspect(_MetaMissing) is None
    payload = MetaGateHostInspector.inspect(_MetaFilled)
    assert payload is not None
    assert payload.node_type == "meta"
    assert dict(payload.node_meta)["description"] == "desc"
    assert MetaGateHostInspector._has_domain_invariant(_MetaFilled) is False
