"""Touch public package exports and thin exception bodies for coverage."""

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


def test_intents_on_public_exports_resolve() -> None:
    pkg = importlib.import_module("action_machine.intents.on")
    for name in ("OnIntent", "on", "BasePluginEvent", "GlobalFinishEvent"):
        obj = getattr(pkg, name)
        assert obj is not None


def test_intents_on_getattr_raises_on_unknown_name() -> None:
    pkg = importlib.import_module("action_machine.intents.on")
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = pkg.NotARealLazyExport


def test_domain_public_exports_resolve() -> None:
    domain = importlib.import_module("action_machine.domain")
    for name in ("BaseDomain", "BaseEntity", "Lifecycle", "Rel", "build", "make"):
        assert getattr(domain, name) is not None


def test_domain_getattr_raises_on_unknown_name() -> None:
    domain = importlib.import_module("action_machine.domain")
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = domain.DefinitelyNotExported


def test_graph_model_leaf_imports_resolve() -> None:
    action_node = importlib.import_module("action_machine.graph_model.nodes.action_graph_node")
    role_edge = importlib.import_module("action_machine.graph_model.edges.role_graph_edge")
    assert action_node.ActionGraphNode is not None
    assert role_edge.RoleGraphEdge is not None


def test_intents_entity_exports_resolve() -> None:
    ent = importlib.import_module("action_machine.intents.entity")
    assert ent.LifeCycleIntentResolver is not None
    assert ent.entity is not None


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


def test_context_requires_exports_intent_surface() -> None:
    ctx_pkg = importlib.import_module("action_machine.intents.context_requires")
    for name in ("ContextRequiresIntent", "ContextRequiresResolver", "ContextView", "Ctx", "context_requires"):
        assert getattr(ctx_pkg, name) is not None


def test_intents_role_mode_lazy_decorator_symbols_resolve() -> None:
    rm = importlib.import_module("action_machine.intents.role_mode")
    assert rm.RoleMode is not None
    assert rm.role_mode is not None


def test_intents_connection_lazy_symbols_resolve() -> None:
    conn = importlib.import_module("action_machine.intents.connection")
    for name in ("ConnectionIntent", "ConnectionInfo", "connection"):
        assert getattr(conn, name) is not None


def test_interchange_vertex_labels_import_resolves() -> None:
    vl = importlib.import_module("action_machine.interchange.vertex_labels")
    assert vl.APPLICATION_VERTEX_TYPE == "Application"
    assert vl.DOMAIN_VERTEX_TYPE == "Domain"
    assert vl.SERVICE_VERTEX_TYPE == "Service"

