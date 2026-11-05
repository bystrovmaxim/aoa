# packages/aoa-action-machine/tests/action_machine/graph/test_events_in_graph.py
"""
Events in the graph and its JSON, read back from the exported document.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One model holds a domain in each mode. Every case reads the document a consumer reads, so it
proves what reaches the file and not what the objects hold.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

_MODULE = __name__


class NobodyNamesItEvent(BaseEvent):
    """Loaded, and declared nowhere."""

    ignored: str = Field(description="Never reaches the graph")


class TypedZoneEvent(BaseEvent):
    """Named by ``@emits`` in a domain with no vocabulary."""

    order_id: str = Field(description="The order")
    plain: int

    @property
    def shout(self) -> str:
        """A class property."""
        return self.order_id.upper()


class SharedEvent(BaseEvent):
    """In two vocabularies, emitted by every kind of method."""


class SpecialSharedEvent(SharedEvent):
    """A subclass is an event of its own."""


class VocabularyOnlyEvent(BaseEvent):
    """Listed, and emitted by nobody."""


class OwnVocabularyEvent(BaseEvent):
    """In a vocabulary that replaces the inherited one."""


class ModeOneDomain(BaseDomain):
    """No switch at all."""

    name = "mode_one"
    description = "Mode 1"


class ModeTwoDomain(BaseDomain):
    """No vocabulary, a typed zone inside."""

    name = "mode_two"
    description = "Mode 2"


class ModeThreeDomain(BaseDomain):
    """A vocabulary."""

    name = "mode_three"
    description = "Mode 3"
    events = (SharedEvent, VocabularyOnlyEvent)


class SecondHomeDomain(BaseDomain):
    """The second home of one event."""

    name = "mode_other"
    description = "Mode 3 again"
    events = (SharedEvent,)


class EmptyVocabularyDomain(BaseDomain):
    """A vocabulary that allows nothing."""

    name = "mode_empty"
    description = "Empty vocabulary"
    events = ()


class InheritedVocabularyDomain(ModeThreeDomain):
    """Takes the parent's vocabulary."""

    name = "mode_inherits"
    description = "Inherited vocabulary"


class ReplacedVocabularyDomain(ModeThreeDomain):
    """Declares its own vocabulary."""

    name = "mode_replaces"
    description = "Replaced vocabulary"
    events = (OwnVocabularyEvent,)


class _Params(BaseParams):
    """Nothing to pass."""


class _Result(BaseResult):
    """Nothing to answer."""


@meta(description="Mode 1", domain=ModeOneDomain)
@check_roles(GuestRole)
class ModeOneAction(BaseAction[_Params, _Result]):
    """Declares nothing."""

    @summary_aspect("Finish")
    async def finish_summary(self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections) -> _Result:
        """Finish."""
        return _Result()


@meta(description="Mode 2", domain=ModeTwoDomain)
@check_roles(GuestRole)
class ModeTwoAction(BaseAction[_Params, _Result]):
    """One typed method."""

    @emits(TypedZoneEvent)
    @summary_aspect("Finish")
    async def finish_summary(self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections) -> _Result:
        """Finish."""
        return _Result()


@meta(description="Mode 3", domain=ModeThreeDomain)
@check_roles(GuestRole)
class ModeThreeAction(BaseAction[_Params, _Result]):
    """One method of every kind, each with ``@emits``."""

    @emits(SharedEvent)
    @regular_aspect("Step")
    async def step_aspect(self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections) -> dict[str, Any]:
        """A step."""
        return {}

    @emits(SharedEvent)
    @summary_aspect("Finish")
    async def finish_summary(self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections) -> _Result:
        """Finish."""
        return _Result()

    @emits(SharedEvent)
    @compensate(step_aspect, "Undo")
    async def undo_compensate(
        self,
        params: _Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        """Undo."""

    @emits(SharedEvent)
    @on_error(ValueError, description="Handle")
    async def handle_on_error(
        self, params: _Params, state: BaseState, box: ToolsBox, connections: Connections, error: Exception
    ) -> _Result:
        """Handle."""
        return _Result()

    @emits(SharedEvent)
    @access_decide("Decide")
    async def decide_access_decide(self, params: _Params, box: ToolsBox, connections: Connections) -> Verdict:
        """Decide."""
        return Allowed()


@meta(description="Inherits its methods", domain=ModeTwoDomain)
@check_roles(GuestRole)
class ModeTwoChildAction(ModeTwoAction):
    """Its emitting methods are those of its own class: none."""


def _id(cls: type) -> str:
    """Return the id a class has in the document."""
    return f"{cls.__module__}.{cls.__qualname__}"


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    """The exported document of everything loaded."""
    parsed: dict[str, Any] = json.loads(create_node_graph_coordinator().to_json())
    return parsed


def _node(document: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    """Return one node row, or ``None``."""
    return next((node for node in document["nodes"] if node["id"] == node_id), None)


def _targets(document: dict[str, Any], source: str, edge_type: str) -> set[str]:
    """Return the targets of ``source``'s edges of one type."""
    return {e["target_id"] for e in document["edges"] if e["source_id"] == source and e["type"] == edge_type}


def _sources(document: dict[str, Any], target: str, edge_type: str) -> set[str]:
    """Return the sources of the edges of one type into ``target``."""
    return {e["source_id"] for e in document["edges"] if e["target_id"] == target and e["type"] == edge_type}


def test_the_document_is_version_1_3(document: dict[str, Any]) -> None:
    assert document["schema_version"] == "1.6"


def test_an_event_nobody_names_has_no_node(document: dict[str, Any]) -> None:
    assert _node(document, _id(NobodyNamesItEvent)) is None


def test_mode_1(document: dict[str, Any]) -> None:
    domain = _id(ModeOneDomain)
    node = _node(document, domain)
    assert node is not None and node["properties"]["typed_events"] is False
    assert _targets(document, domain, "domain_event") == set()
    assert _targets(document, f"{_id(ModeOneAction)}:finish_summary", "@emits") == set()


def test_mode_2(document: dict[str, Any]) -> None:
    domain = _id(ModeTwoDomain)
    node = _node(document, domain)
    assert node is not None and node["properties"]["typed_events"] is False
    assert _targets(document, domain, "domain_event") == set()
    assert _targets(document, f"{_id(ModeTwoAction)}:finish_summary", "@emits") == {_id(TypedZoneEvent)}


def test_mode_3(document: dict[str, Any]) -> None:
    domain = _id(ModeThreeDomain)
    node = _node(document, domain)
    assert node is not None and node["properties"]["typed_events"] is True
    assert _targets(document, domain, "domain_event") == {_id(SharedEvent), _id(VocabularyOnlyEvent)}


@pytest.mark.parametrize("method", ["step_aspect", "finish_summary", "undo_compensate", "handle_on_error", "decide_access_decide"])
def test_each_kind_of_method_gives_its_edge(document: dict[str, Any], method: str) -> None:
    assert _targets(document, f"{_id(ModeThreeAction)}:{method}", "@emits") == {_id(SharedEvent)}


def test_an_event_named_many_times_is_one_node(document: dict[str, Any]) -> None:
    shared = _id(SharedEvent)
    assert len([node for node in document["nodes"] if node["id"] == shared]) == 1
    assert {_id(ModeThreeDomain), _id(SecondHomeDomain)} <= _sources(document, shared, "domain_event")


def test_an_empty_vocabulary_is_a_vocabulary(document: dict[str, Any]) -> None:
    domain = _id(EmptyVocabularyDomain)
    node = _node(document, domain)
    assert node is not None and node["properties"]["typed_events"] is True
    assert _targets(document, domain, "domain_event") == set()


def test_an_inherited_vocabulary_counts(document: dict[str, Any]) -> None:
    domain = _id(InheritedVocabularyDomain)
    node = _node(document, domain)
    assert node is not None and node["properties"]["typed_events"] is True
    assert _targets(document, domain, "domain_event") == {_id(SharedEvent), _id(VocabularyOnlyEvent)}


def test_a_declared_vocabulary_replaces_the_inherited_one(document: dict[str, Any]) -> None:
    assert _targets(document, _id(ReplacedVocabularyDomain), "domain_event") == {_id(OwnVocabularyEvent)}


def test_a_listed_event_nobody_emits_has_no_emits_edge(document: dict[str, Any]) -> None:
    event = _id(VocabularyOnlyEvent)
    assert _node(document, event) is not None
    assert _sources(document, event, "@emits") == set()


def test_a_subclass_of_a_listed_event_is_not_that_event(document: dict[str, Any]) -> None:
    assert _node(document, _id(SpecialSharedEvent)) is None


def test_an_inherited_method_gives_no_edge(document: dict[str, Any]) -> None:
    assert _id(ModeTwoChildAction) not in {
        source.split(":")[0] for source in _sources(document, _id(TypedZoneEvent), "@emits")
    }


def test_an_event_node_is_shaped_like_params(document: dict[str, Any]) -> None:
    event = _id(TypedZoneEvent)
    assert _node(document, event) == {"id": event, "type": "Event", "label": "TypedZoneEvent", "properties": {}}


def test_an_event_with_no_fields_has_no_field_edges(document: dict[str, Any]) -> None:
    assert _targets(document, _id(SharedEvent), "field") == set()


def test_own_fields_only_and_their_descriptions(document: dict[str, Any]) -> None:
    event = _id(TypedZoneEvent)
    assert _targets(document, event, "field") == {f"{event}:order_id", f"{event}:plain"}
    written = _node(document, f"{event}:order_id")
    missing = _node(document, f"{event}:plain")
    assert written is not None and written["properties"]["description"] == "The order"
    assert missing is not None and missing["properties"]["description"] == ""


def test_a_class_property_is_a_property_field(document: dict[str, Any]) -> None:
    event = _id(TypedZoneEvent)
    targets = _targets(document, event, "property")
    assert len(targets) == 1
    node = _node(document, targets.pop())
    assert node is not None and (node["type"], node["label"]) == ("PropertyField", "shout")


def test_the_edges_have_their_nature(document: dict[str, Any]) -> None:
    natures = {(e["type"], e["relationship"], e["is_dag"]) for e in document["edges"] if e["type"] in {"@emits", "domain_event"}}
    assert natures == {("@emits", "Association", False), ("domain_event", "Aggregation", False)}


def test_two_builds_give_the_same_document(document: dict[str, Any]) -> None:
    assert json.loads(create_node_graph_coordinator().to_json()) == document


def test_a_document_passes_its_schema(document: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA

    assert list(Draft202012Validator(GRAPH_JSON_SCHEMA).iter_errors(document)) == []
