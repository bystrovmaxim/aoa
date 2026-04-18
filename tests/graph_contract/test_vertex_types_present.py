# tests/graph_contract/test_vertex_types_present.py

"""
PR5 matrix (plan 009): interchange ``node_type`` values from the samples narrow graph.

Full ``VERTEX_TYPES`` coverage with stubs or skips is PR11; here we lock the
subset produced by ``build_sample_coordinator()`` today.
"""

from __future__ import annotations

import importlib

import pytest

from action_machine.domain.application_context import ApplicationContext
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.build import _MODULES, build_sample_coordinator
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.store.actions.checkout_submit import CheckoutSubmitAction
from maxitor.samples.store.domain import StoreDomain

# Core kinds always present on samples interchange; other facet ``node_type`` strings may appear.
_SAMPLES_LOGICAL_VERTEX_TYPES: frozenset[str] = frozenset(
    {"Action", "application", "domain", "role_class", "entity"},
)


def _import_sample_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


@pytest.mark.graph_coverage
def test_vertex_types_matrix_samples_narrow_projection() -> None:
    _import_sample_modules()
    lg = build_sample_coordinator().get_graph()
    present = {lg[idx]["node_type"] for idx in lg.node_indices()}
    assert present >= _SAMPLES_LOGICAL_VERTEX_TYPES


@pytest.mark.graph_coverage
def test_c2_single_action_vertex_for_checkout_submit_action() -> None:
    """One interchange ``action`` vertex per qualname (CheckoutSubmitAction)."""
    _import_sample_modules()
    lg = build_sample_coordinator().get_graph()
    action_id = BaseIntentInspector._make_node_name(CheckoutSubmitAction)
    matches = [lg[i] for i in lg.node_indices() if lg[i]["id"] == action_id]
    assert len(matches) == 1
    assert matches[0]["node_type"] == "Action"


@pytest.mark.graph_coverage
def test_c2_single_domain_vertex_per_bounded_context() -> None:
    """Each sample ``BaseDomain`` maps to exactly one interchange ``domain`` vertex."""
    _import_sample_modules()
    lg = build_sample_coordinator().get_graph()
    for domain_cls in (StoreDomain, BillingDomain, MessagingDomain, CatalogDomain):
        domain_id = BaseIntentInspector._make_node_name(domain_cls)
        matches = [lg[i] for i in lg.node_indices() if lg[i]["id"] == domain_id]
        assert len(matches) == 1, domain_cls
        assert matches[0]["node_type"] == "domain"


@pytest.mark.graph_coverage
def test_single_application_vertex_and_domain_belongs_to_application() -> None:
    """Canonical ``application`` node; each domain has ``BELONGS_TO`` → application."""
    _import_sample_modules()
    lg = build_sample_coordinator().get_graph()
    app_id = BaseIntentInspector._make_node_name(ApplicationContext)
    app_nodes = [lg[i] for i in lg.node_indices() if lg[i]["id"] == app_id]
    assert len(app_nodes) == 1
    assert app_nodes[0]["node_type"] == "application"
    id_by_idx = {i: lg[i]["id"] for i in lg.node_indices()}
    for domain_cls in (StoreDomain, BillingDomain, MessagingDomain, CatalogDomain):
        domain_id = BaseIntentInspector._make_node_name(domain_cls)
        forward = [
            w
            for s, t, w in lg.weighted_edge_list()
            if id_by_idx[s] == domain_id
            and id_by_idx[t] == app_id
            and w["edge_type"] == "BELONGS_TO"
            and w["category"] == "direct"
        ]
        assert forward, domain_cls
