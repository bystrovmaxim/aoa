# packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_signature.py
"""
The signature an aspect declaration must have — the table, and later its validators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The four declaration decorators mark methods the machine calls itself: it hands over a
fixed set of values, in one order, and reads one answer back. What a declaration receives
is therefore the contract, and a declaration that renames, reorders or leaves untyped any
of it is not a shorter form of the same thing — it is a different, wrong one, which still
runs because Python binds by position.

This module holds the four contracts as **data**: for each decorator, the parameter names
in order, the type each of them must resolve to, and the rule its return must satisfy.
The decorators, the interchange graph nodes and the tests read the same table, so a rule
cannot drift between the place that refuses it and the place that documents it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @summary_aspect ──┐
    @regular_aspect ──┤
    @on_error       ──┼──▶ ASPECT_CONTRACTS[kind] ──▶ shape refusals (declaration)
    @compensate     ──┘                          └──▶ type refusals  (assembly)

Two moments, because Python makes them different: what needs no name resolution — the
count, the names in order, the presence of annotations, positional callability — is
refused where the method is written; what needs the operation's own ``Params`` and
``Result`` to exist is refused when the capability is assembled.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the four contracts and the rules their entries must satisfy.

OUT: the validators that apply them (next to this module's stories), and what a
declaration answers at run time — that belongs to the executor and to
``ActionResultTypeError``.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.aspects.aspect_signature import ASPECT_CONTRACTS

    contract = ASPECT_CONTRACTS["summary_aspect"]
    contract.parameters             # ("self", "params", "state", "box", "connections")
    contract.parameters_with_ctx    # the same, plus the trailing "ctx"
    contract.expected_types["box"]  # ToolsBox
    contract.return_rule            # "operation_result"
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

ReturnRule = Literal["operation_result", "state_fragment", "none"]
"""What a declaration's return must be: the operation's ``Result``, a state fragment, or nothing."""

_BASE_PARAMETERS: tuple[str, ...] = ("self", "params", "state", "box", "connections")
"""The parameters the pipeline hands to every aspect, in the order it hands them over."""

_BASE_TYPES: Mapping[str, Any] = MappingProxyType(
    {
        "params": BaseParams,
        "state": BaseState,
        "box": ToolsBox,
        "connections": dict[str, BaseResource],
        "ctx": ContextView,
    },
)
"""The type each base parameter must resolve to; ``ctx`` is present only when context was asked for."""

_COMPENSATE_PARAMETERS: tuple[str, ...] = (
    "self",
    "params",
    "state_before",
    "state_after",
    "box",
    "connections",
    "error",
)
"""The compensator's parameters: two states, because it is called after one was replaced."""

_COMPENSATE_TYPES: Mapping[str, Any] = MappingProxyType(
    {
        "params": BaseParams,
        "state_before": BaseState,
        "state_after": BaseState | None,
        "box": ToolsBox,
        "connections": dict[str, BaseResource],
        "error": Exception,
        "ctx": ContextView,
    },
)
"""The compensator's types: ``state_after`` is ``None`` when the compensated aspect did not finish."""


@dataclass(frozen=True)
class AspectContract:
    """
    AI-CORE-BEGIN
    ROLE: One declaration decorator's signature as data: what it receives, when ``ctx`` is added, what each value must be typed as, and what its return must be.
    CONTRACT: ``parameters`` starts with ``self`` and lists the values in the order the pipeline passes them; ``parameters_with_ctx`` is exactly ``parameters`` plus the trailing ``ctx``; ``expected_types`` names only parameters that exist in ``parameters``; ``return_rule`` is one of ``operation_result``, ``state_fragment``, ``none``. The object is frozen, so a contract cannot be altered after it is built.
    INVARIANTS: Every decorator has one entry in ``ASPECT_CONTRACTS`` and no two entries share a ``kind``. A violation of the fields above is a defect of this module, not a fact about a declaration, and is caught by ``test_aspect_contract_table.py`` rather than at run time.
    AI-CORE-END
    """

    kind: str
    parameters: tuple[str, ...]
    parameters_with_ctx: tuple[str, ...]
    expected_types: Mapping[str, Any]
    return_rule: ReturnRule


ASPECT_CONTRACTS: Mapping[str, AspectContract] = MappingProxyType(
    {
        "summary_aspect": AspectContract(
            kind="summary_aspect",
            parameters=_BASE_PARAMETERS,
            parameters_with_ctx=(*_BASE_PARAMETERS, "ctx"),
            expected_types=_BASE_TYPES,
            return_rule="operation_result",
        ),
        "regular_aspect": AspectContract(
            kind="regular_aspect",
            parameters=_BASE_PARAMETERS,
            parameters_with_ctx=(*_BASE_PARAMETERS, "ctx"),
            expected_types=_BASE_TYPES,
            return_rule="state_fragment",
        ),
        "on_error": AspectContract(
            kind="on_error",
            parameters=(*_BASE_PARAMETERS, "error"),
            parameters_with_ctx=(*_BASE_PARAMETERS, "error", "ctx"),
            expected_types=MappingProxyType({**_BASE_TYPES, "error": Exception}),
            return_rule="operation_result",
        ),
        "compensate": AspectContract(
            kind="compensate",
            parameters=_COMPENSATE_PARAMETERS,
            parameters_with_ctx=(*_COMPENSATE_PARAMETERS, "ctx"),
            expected_types=_COMPENSATE_TYPES,
            return_rule="none",
        ),
    },
)
"""The four declaration contracts, keyed by the decorator's name without the ``@``."""

__all__ = ["ASPECT_CONTRACTS", "AspectContract", "ReturnRule"]
