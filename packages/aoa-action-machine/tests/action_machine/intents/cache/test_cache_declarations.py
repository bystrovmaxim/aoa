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
import types
from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.aspect_signature_error import AspectSignatureError
from aoa.action_machine.exceptions.cache_contract_error import CacheContractError
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

from ....support.cache_model import CachedItemCoreEntity, CachedReportCoreEntity
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

    @cache_write("Keep every order", tags=(CachedItemCoreEntity,))
    async def order_cache_write(
        self, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult, duration_ms: float
    ) -> list[CacheTag] | None:
        _seen["write_duration"] = duration_ms
        return [CacheTag(type=CachedItemCoreEntity, key=params.order_id)]

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

        @cache_invalidate("Drop", tags=(CachedItemCoreEntity,))
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

        @cache_write("Write", tags=(CachedItemCoreEntity,))
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

        @cache_write("Write", tags=(CachedItemCoreEntity,))
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


# ─── 11.2: a key and a write come together ──────────────────────────────────


async def _key(self: Any, params: OrderParams, box: ToolsBox, connections: Connections) -> str | None:
    return "k"


async def _read(self: Any, params: OrderParams, box: ToolsBox, connections: Connections, entry: CacheEntry) -> OrderResult | None:
    return None


async def _write(
    self: Any, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult, duration_ms: float
) -> list[CacheTag] | None:
    return None


async def _invalidate(self: Any, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult) -> list[CacheTag] | None:
    return None


def _declared(name: str, decorator: Any, func: Any) -> Any:
    func.__name__ = func.__qualname__ = name
    return decorator(func)


def _action_with(name: str, **methods: Any) -> type:
    return type(name, (BaseAction,), {"__module__": __name__, **methods})


def _fresh(func: Any) -> Any:
    """A copy of ``func``, so each declaration gets its own name and mark."""
    copy = types.FunctionType(func.__code__, func.__globals__, func.__name__, func.__defaults__, func.__closure__)
    copy.__annotations__ = dict(func.__annotations__)
    return copy


@pytest.mark.parametrize(
    ("declared_kinds", "message"),
    [
        (("key",), "KeyOnlyAction declares @cache_key without @cache_write; a key without a write never stores anything."),
        (("write",), "WriteOnlyAction declares @cache_write without @cache_key; the machine calls a write only for a key."),
        (("read",), "ReadOnlyAction declares @cache_read without @cache_key and @cache_write; nothing is ever stored for it to read."),
        (("key", "read"), "KeyReadAction declares @cache_key without @cache_write; a key without a write never stores anything."),
    ],
)
def test_a_key_a_write_and_a_read_come_together(declared_kinds: tuple[str, ...], message: str) -> None:
    """Case 11.2: each one alone is refused when the class is created."""
    templates = {"key": (cache_key, _key), "read": (cache_read, _read), "write": (cache_write, _write)}
    name = {("key",): "KeyOnlyAction", ("write",): "WriteOnlyAction", ("read",): "ReadOnlyAction", ("key", "read"): "KeyReadAction"}[declared_kinds]
    methods = {
        f"x_cache_{kind}": _declared(f"x_cache_{kind}", templates[kind][0]("Declared"), _fresh(templates[kind][1]))
        for kind in declared_kinds
    }
    with pytest.raises(DeclarationStructureError, match=re.escape(message)):
        _action_with(name, **methods)


def test_an_invalidation_may_stand_alone() -> None:
    """An action that changes data drops what others cached and caches nothing itself."""
    _action_with("UpdateOnlyAction", x_cache_invalidate=_declared("x_cache_invalidate", cache_invalidate("Drop", tags=(CachedItemCoreEntity,)), _fresh(_invalidate)))


def test_a_key_with_a_write_and_a_read_is_accepted() -> None:
    """The full set is accepted."""
    _action_with(
        "FullCacheAction",
        x_cache_key=_declared("x_cache_key", cache_key("Key"), _fresh(_key)),
        x_cache_read=_declared("x_cache_read", cache_read("Read"), _fresh(_read)),
        x_cache_write=_declared("x_cache_write", cache_write("Write"), _fresh(_write)),
    )


# ─── 11.4: tags carry declared types ────────────────────────────────────────


_returned: dict[str, list[CacheTag]] = {}


@meta(description="Returns whatever tags the test sets", domain=OrdersDomain)
@check_roles(GuestRole)
class TaggingAction(BaseAction[OrderParams, OrderResult]):
    """A writer and an invalidator of items, returning the tags a test chooses."""

    @cache_key("Order")
    async def tagging_cache_key(self, params: OrderParams, box: ToolsBox, connections: Connections) -> str | None:
        return params.order_id

    @cache_write("Keep items", tags=(CachedItemCoreEntity,))
    async def tagging_cache_write(
        self, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return _returned.get("write", [])

    @cache_invalidate("Drop items", tags=(CachedItemCoreEntity,))
    async def tagging_cache_invalidate(
        self, params: OrderParams, box: ToolsBox, connections: Connections, result: OrderResult
    ) -> list[CacheTag] | None:
        return _returned.get("invalidate", [])

    @summary_aspect("Load")
    async def load_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        return OrderResult(order_id=params.order_id, run=0)


async def test_a_tag_of_a_declared_type_is_stored() -> None:
    """The entry is written under the tag the write returned."""
    _returned.clear()
    _returned["write"] = [CacheTag(type=CachedItemCoreEntity, key="o1")]
    cache = CacheCoordinator()
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=cache)
    await machine.run(_caller(), TaggingAction(), OrderParams(order_id="o1"))
    assert await cache.evict_by_tags(frozenset({CacheTag(type=CachedItemCoreEntity, key="o1")})) == 1


@pytest.mark.parametrize("step", ["write", "invalidate"])
@pytest.mark.parametrize(
    ("tag", "message"),
    [
        (CacheTag(type=CachedReportCoreEntity, key="r1"), "whose type CachedReportCoreEntity is not among its declared tags (CachedItemCoreEntity)"),
        (CacheTag(key="o1"), "which has no type; a tag names one of its declared types (CachedItemCoreEntity)"),
    ],
    ids=["undeclared-type", "no-type"],
)
async def test_a_returned_tag_must_be_of_a_declared_type(step: str, tag: CacheTag, message: str) -> None:
    """Case 11.4: a tag of an undeclared type, or without a type, fails the call naming the action and the tag."""
    _returned.clear()
    _returned[step] = [tag]
    with pytest.raises(CacheContractError, match=re.escape(f"TaggingAction.tagging_cache_{step} returned {tag!r}, {message}")):
        await _machine().run(_caller(), TaggingAction(), OrderParams(order_id="o9"))


def test_an_invalidation_declares_at_least_one_type() -> None:
    """An invalidation without a type drops nothing, refused when the class body runs."""
    with pytest.raises(DeclarationStructureError, match="declare the entity types it drops"):
        cache_invalidate("Drop", tags=())


def test_a_tag_type_is_an_entity_class() -> None:
    """The graph links an action to each tag type, so a tag type is an entity."""
    with pytest.raises(DeclarationStructureError, match=r"\['OrderResult'\] are not"):
        cache_write("Write", tags=(OrderResult,))
