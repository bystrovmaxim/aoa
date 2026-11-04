# packages/aoa-action-machine/tests/action_machine/intents/cache/test_cache_declarations.py
"""
The cache is four declarations with the rules of ``@access_decide``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 11.1 and 11.6 of issue #412: ``@cache_key``, ``@cache_read``, ``@cache_write``
and ``@cache_invalidate`` take a description, sit on an ``async`` method with their
suffix and a fixed signature, appear at most once of a kind and are not inherited;
the machine calls them; a method under an old hook name is refused. Actions that
must be refused are declared inside their test, so a refused class never reaches
the graph another test builds.
"""

from __future__ import annotations

import inspect
import re
from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.aspect_signature_error import AspectSignatureError
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.description_contract_error import DescriptionContractError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import cache_invalidate, cache_key, cache_read, cache_write
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import OrdersDomain

_runs: dict[str, int] = {}
_seen: dict[str, Any] = {}


class OrderParams(BaseParams):
    """One order."""

    order_id: str = Field(description="Order id")


class OrderResult(BaseResult):
    """The order and how many times the pipeline ran."""

    order_id: str = Field(description="Order id")
    run: int = Field(description="Pipeline run ordinal")


@meta(description="Get an order, cached per user", domain=OrdersDomain)
@check_roles(GuestRole)
class GetCachedOrderAction(BaseAction[OrderParams, OrderResult]):
    """Declares a key that asks for context, a read and a write."""

    @cache_key("Order by user and id")
    @context_requires("user.user_id")
    async def order_cache_key(
        self, params: OrderParams, box: ToolsBox, connections: Connections, ctx: ContextView
    ) -> str | None:
        return f"{ctx.get('user.user_id')}:order:{params.order_id}"

    @cache_read("Keep a hit unless asked to refuse it")
    async def order_cache_read(
        self, params: OrderParams, box: ToolsBox, connections: Connections, entry: CacheEntry
    ) -> OrderResult | None:
        _seen["read_box"] = box
        return None if _seen.get("refuse_read") else entry.result  # type: ignore[return-value]

    @cache_write("Keep every order")
    async def order_cache_write(
        self, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult, duration_ms: float
    ) -> list[CacheTag] | None:
        _seen["write_duration"] = duration_ms
        return [CacheTag(key=params.order_id)]

    @summary_aspect("Load the order")
    async def load_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        _runs["get"] = _runs.get("get", 0) + 1
        return OrderResult(order_id=params.order_id, run=_runs["get"])


@meta(description="A subclass that declares nothing", domain=OrdersDomain)
@check_roles(GuestRole)
class InheritingOrderAction(GetCachedOrderAction):
    """Declarations are not inherited, so this one caches nothing."""

    @summary_aspect("Load the order again")
    async def reload_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        _runs["inherit"] = _runs.get("inherit", 0) + 1
        return OrderResult(order_id=params.order_id, run=_runs["inherit"])


def _machine() -> ActionProductMachine:
    return ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=CacheCoordinator())


def _caller(user_id: str = "u1") -> Context:
    return Context(user=UserInfo(user_id=user_id, roles=(GuestRole,)))


async def test_a_declared_cache_hits_and_the_key_reads_its_context() -> None:
    """Case 11.1: the second run with the same user and id is a hit; another user misses."""
    _runs.clear()
    _seen.clear()
    machine = _machine()
    first = await machine.run(_caller(), GetCachedOrderAction(), OrderParams(order_id="o1"))
    second = await machine.run(_caller(), GetCachedOrderAction(), OrderParams(order_id="o1"))
    other_user = await machine.run(_caller("u2"), GetCachedOrderAction(), OrderParams(order_id="o1"))
    assert (first.run, second.run, other_user.run) == (1, 1, 2)
    assert _seen["write_duration"] >= 0
    assert isinstance(_seen["read_box"], ToolsBox)


async def test_a_read_returning_none_drops_the_entry_and_runs() -> None:
    """``@cache_read`` returning ``None`` treats the entry as stale."""
    _runs.clear()
    _seen.clear()
    machine = _machine()
    await machine.run(_caller(), GetCachedOrderAction(), OrderParams(order_id="o2"))
    _seen["refuse_read"] = True
    again = await machine.run(_caller(), GetCachedOrderAction(), OrderParams(order_id="o2"))
    assert again.run == 2


async def test_a_subclass_does_not_inherit_the_declarations() -> None:
    """A subclass caches only what it declares itself."""
    _runs.clear()
    _seen.clear()
    machine = _machine()
    first = await machine.run(_caller(), InheritingOrderAction(), OrderParams(order_id="o3"))
    second = await machine.run(_caller(), InheritingOrderAction(), OrderParams(order_id="o3"))
    assert (first.run, second.run) == (1, 2)


def test_base_action_has_none_of_the_old_hooks() -> None:
    """Case 11.6: the machine calls only declarations."""
    assert [name for name in ("cache_key", "read_cache", "on_cache_write", "on_cache_invalidate") if hasattr(BaseAction, name)] == []


@pytest.mark.parametrize(
    ("old_name", "replacement"),
    [
        ("cache_key", "@cache_key"),
        ("read_cache", "@cache_read"),
        ("on_cache_write", "@cache_write"),
        ("on_cache_invalidate", "@cache_invalidate"),
    ],
)
def test_a_method_under_an_old_hook_name_is_refused(old_name: str, replacement: str) -> None:
    """Case 11.6: a method the machine no longer calls is dead code, refused when the class is created."""

    async def old_hook(self: Any, *args: Any) -> None:
        return None

    with pytest.raises(DeclarationStructureError, match=rf"OldHookAction\.{old_name} is a cache hook .* {replacement}"):
        type("OldHookAction", (BaseAction,), {old_name: old_hook, "__module__": __name__})


def test_two_declarations_of_one_kind_are_refused_naming_both() -> None:
    """At most one of each kind on an action."""
    with pytest.raises(DeclarationStructureError, match=r"declares @cache_key more than once \(first_cache_key, second_cache_key\)"):

        class TwoKeysAction(BaseAction[OrderParams, OrderResult]):
            @cache_key("One")
            async def first_cache_key(self, params: OrderParams, box: ToolsBox, connections: Connections) -> str | None:
                return "a"

            @cache_key("Two")
            async def second_cache_key(self, params: OrderParams, box: ToolsBox, connections: Connections) -> str | None:
                return "b"


def test_a_declaration_needs_a_description() -> None:
    """The first argument is a non-empty description."""
    with pytest.raises(DescriptionContractError):
        cache_write("   ")


def test_a_declaration_needs_its_suffix() -> None:
    """The method's name ends with its kind."""
    with pytest.raises(NamingSuffixError, match="must end with '_cache_invalidate'"):

        @cache_invalidate("Drop")
        async def drop(self: Any, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult) -> list[CacheTag] | None:
            return None


def test_a_declaration_must_be_async() -> None:
    """Only ``async def``."""
    with pytest.raises(DeclarationStructureError, match="must be async"):

        @cache_key("Key")
        def plain_cache_key(self: Any, params: OrderParams, box: ToolsBox, connections: Connections) -> str | None:
            return None


def test_a_declaration_keeps_its_parameters_in_order() -> None:
    """Names and order are the contract; a swap is refused when the class body runs."""
    with pytest.raises(AspectSignatureError, match=r"\(self, params, box, connections, result, duration_ms\)"):

        @cache_write("Write")
        async def swapped_cache_write(
            self: Any, params: OrderParams, box: ToolsBox, connections: Connections, duration_ms: float, result: OrderResult
        ) -> list[CacheTag] | None:
            return None


def test_a_declaration_annotates_every_parameter() -> None:
    """A missing annotation is refused when the class body runs."""
    with pytest.raises(AspectSignatureError, match=r"\(entry\) carry no annotation"):

        @cache_read("Read")
        async def bare_cache_read(self: Any, params: OrderParams, box: ToolsBox, connections: Connections, entry) -> OrderResult | None:  # type: ignore[no-untyped-def]
            return None


def test_context_requires_above_the_declaration_is_explained() -> None:
    """``@context_requires`` must sit under the cache decorator."""
    with pytest.raises(AspectSignatureError, match=re.escape("put @context_requires(...) under @cache_key")):

        @context_requires("user.user_id")
        @cache_key("Key")
        async def scoped_cache_key(
            self: Any, params: OrderParams, box: ToolsBox, connections: Connections, ctx: ContextView
        ) -> str | None:
            return None


def test_a_wrong_annotation_type_is_refused_at_assembly() -> None:
    """Types are checked when the graph is assembled, where the operation's names resolve."""

    @meta(description="Annotates duration_ms as a string", domain=OrdersDomain)
    @check_roles(GuestRole)
    class WrongTypeAction(BaseAction[OrderParams, OrderResult]):
        @cache_key("Key")
        async def wrong_cache_key(self, params: OrderParams, box: ToolsBox, connections: Connections) -> str | None:
            return "k"

        @cache_write("Write")
        async def wrong_cache_write(
            self, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult, duration_ms: str
        ) -> list[CacheTag] | None:
            return None

        @summary_aspect("Load")
        async def load_summary(
            self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
        ) -> OrderResult:
            return OrderResult(order_id="o", run=0)

    with pytest.raises(AspectSignatureError, match=r"WrongTypeAction\.wrong_cache_write annotates 'duration_ms' as str"):
        ActionGraphNode(WrongTypeAction)


def test_the_signatures_are_the_contract_of_the_issue() -> None:
    """Every kind starts with self, params, box, connections."""
    names = {
        name: tuple(inspect.signature(getattr(GetCachedOrderAction, name)).parameters)
        for name in ("order_cache_key", "order_cache_read", "order_cache_write")
    }
    assert names == {
        "order_cache_key": ("self", "params", "box", "connections", "ctx"),
        "order_cache_read": ("self", "params", "box", "connections", "entry"),
        "order_cache_write": ("self", "params", "box", "connections", "result", "duration_ms"),
    }
