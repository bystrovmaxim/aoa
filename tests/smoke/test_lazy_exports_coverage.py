"""Touch lazy ``__getattr__`` re-exports and thin exception bodies for coverage."""

from __future__ import annotations

import importlib

import pytest

from action_machine.exceptions.action_result_type_error import ActionResultTypeError
from action_machine.exceptions.missing_entity_info_error import MissingEntityInfoError
from action_machine.exceptions.on_error_handler_error import OnErrorHandlerError


def test_exception_constructors_set_attributes() -> None:
    e1 = ActionResultTypeError("bad", expected_type=int, actual_type=str)
    assert e1.expected_type is int and e1.actual_type is str

    inner = RuntimeError("x")
    e2 = OnErrorHandlerError("wrapped", "my_handler", inner)
    assert e2.handler_name == "my_handler" and e2.original_error is inner

    e3 = MissingEntityInfoError(float, key="description")
    assert e3.host_cls is float and e3.key == "description"


def test_intents_on_lazy_plugin_exports_resolve() -> None:
    pkg = importlib.import_module("action_machine.intents.on")
    for name in ("Plugin", "PluginCoordinator", "PluginRunContext", "SubscriptionInfo"):
        obj = getattr(pkg, name)
        assert obj is not None


def test_intents_on_getattr_raises_on_unknown_name() -> None:
    pkg = importlib.import_module("action_machine.intents.on")
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = pkg.NotARealLazyExport


def test_domain_lazy_graph_and_entity_decorator_resolve() -> None:
    domain = importlib.import_module("action_machine.domain")
    for name in (
        "entity",
        "DomainGraphNode",
        "DomainGraphNodeInspector",
        "EntityGraphNode",
        "EntityGraphNodeInspector",
    ):
        assert getattr(domain, name) is not None


def test_domain_getattr_raises_on_unknown_name() -> None:
    domain = importlib.import_module("action_machine.domain")
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = domain.DefinitelyNotExported


def test_graph_model_edges_lazy_exports_resolve() -> None:
    edges = importlib.import_module("action_machine.graph_model.edges")
    for name in edges.__all__:
        assert getattr(edges, name) is not None


def test_intents_entity_lazy_inspector_symbols_resolve() -> None:
    ent = importlib.import_module("action_machine.intents.entity")
    assert ent.DomainGraphNode is not None
    assert ent.EntityIntentInspector is not None


def test_intents_meta_lazy_meta_decorator_resolve() -> None:
    meta_pkg = importlib.import_module("action_machine.intents.meta")
    meta_fn = meta_pkg.meta
    assert callable(meta_fn)
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = meta_pkg.undefined_meta_symbol


def test_auth_lazy_pipeline_symbols_resolve() -> None:
    auth = importlib.import_module("action_machine.auth")
    for name in (
        "Authenticator",
        "AuthCoordinator",
        "ContextAssembler",
        "CredentialExtractor",
        "NoAuthCoordinator",
    ):
        assert getattr(auth, name) is not None


def test_context_requires_lazy_context_types_resolve() -> None:
    ctx_pkg = importlib.import_module("action_machine.intents.context_requires")
    for name in ("Context", "RequestInfo", "RuntimeInfo", "UserInfo"):
        assert getattr(ctx_pkg, name) is not None
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = ctx_pkg.NotLazyContextExport


def test_intents_role_mode_lazy_decorator_symbols_resolve() -> None:
    rm = importlib.import_module("action_machine.intents.role_mode")
    assert rm.RoleMode is not None
    assert rm.role_mode is not None


def test_intents_connection_lazy_symbols_resolve() -> None:
    conn = importlib.import_module("action_machine.intents.connection")
    for name in ("ConnectionIntent", "ConnectionInfo", "connection"):
        assert getattr(conn, name) is not None


def test_legacy_lazy_getattr_success_and_failure() -> None:
    leg = importlib.import_module("action_machine.legacy")
    assert leg.Core is not None
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = leg.DefinitelyNotInLegacyAll
    names = leg.__dir__()
    assert "Core" in names


def test_legacy_every_public_lazy_name_materializes_once() -> None:
    """PEP 562 registry on ``legacy`` stays complete and importable (CI gate for cycles)."""

    leg = importlib.import_module("action_machine.legacy")
    for export in sorted(leg.__all__):
        assert getattr(leg, export) is not None
