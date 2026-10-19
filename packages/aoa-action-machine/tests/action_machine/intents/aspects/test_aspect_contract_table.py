# packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_contract_table.py
"""
Tests for the contract table itself — the invariants every entry must satisfy.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ASPECT_CONTRACTS`` is the single place the four declaration signatures are written
down. Every refusal of the coming stories reads it, so a typo here would be a rule the
framework enforces and documents — which is exactly the defect the feature exists to
remove. These tests pin the table's own shape: each entry lists ``self`` first, the
``ctx`` variant is the plain one plus ``ctx``, every declared type belongs to a declared
parameter, the kinds match the four decorators, and the table cannot be edited at run time.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheFourContracts       — one entry per decorator, keyed by the decorator's name
TestEachEntryIsWellFormed  — names start with ``self``, ``ctx`` is last, types fit the names
TestTheOrders              — the exact orders, quoted from contracts/declaration-contract.md
TestTheReturnRules         — which return each decorator promises
TestImmutability           — a contract cannot be altered after it is built
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.intents.aspects.aspect_signature import ASPECT_CONTRACTS, AspectContract
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

EXPLAINED_ORDER = "contracts/declaration-contract.md"
"""Where the orders asserted below are written down for a reader."""


class TestTheFourContracts:
    """One entry per decorator, keyed by the decorator's name without the ``@``."""

    def test_every_decorator_has_a_contract(self) -> None:
        assert set(ASPECT_CONTRACTS) == {"summary_aspect", "regular_aspect", "on_error", "compensate"}

    def test_a_contract_is_keyed_by_its_own_kind(self) -> None:
        for key, contract in ASPECT_CONTRACTS.items():
            assert contract.kind == key, f"{key}: contract.kind is {contract.kind!r}"

    def test_a_contract_is_an_aspect_contract(self) -> None:
        for contract in ASPECT_CONTRACTS.values():
            assert isinstance(contract, AspectContract)


class TestEachEntryIsWellFormed:
    """Names start with ``self``, ``ctx`` is last, and the types fit the names."""

    def test_the_first_parameter_is_self(self) -> None:
        for kind, contract in ASPECT_CONTRACTS.items():
            assert contract.parameters[0] == "self", f"{kind}: first parameter is {contract.parameters[0]!r}"

    def test_the_ctx_variant_is_the_plain_one_plus_ctx(self) -> None:
        for kind, contract in ASPECT_CONTRACTS.items():
            assert contract.parameters_with_ctx == (*contract.parameters, "ctx"), (
                f"{kind}: parameters_with_ctx is not parameters + ('ctx',) — see {EXPLAINED_ORDER}"
            )

    def test_only_ctx_may_be_typed_without_being_a_plain_parameter(self) -> None:
        for kind, contract in ASPECT_CONTRACTS.items():
            outside = set(contract.expected_types) - set(contract.parameters)
            assert outside <= {"ctx"}, f"{kind}: {sorted(outside)} are typed but not declared"

    def test_every_parameter_except_self_is_typed(self) -> None:
        for kind, contract in ASPECT_CONTRACTS.items():
            declared = set(contract.parameters_with_ctx) - {"self"}
            assert set(contract.expected_types) == declared, (
                f"{kind}: typed {sorted(contract.expected_types)}, declared {sorted(declared)}"
            )

    def test_the_base_types_are_the_contract_types(self) -> None:
        for kind in ("summary_aspect", "regular_aspect", "on_error"):
            types = ASPECT_CONTRACTS[kind].expected_types
            assert types["params"] is BaseParams, kind
            assert types["state"] is BaseState, kind
            assert types["box"] is ToolsBox, kind
            assert types["connections"] == Connections, kind
            assert types["ctx"] is ContextView, kind

    def test_the_error_is_the_root_exception(self) -> None:
        assert ASPECT_CONTRACTS["on_error"].expected_types["error"] is Exception
        assert ASPECT_CONTRACTS["compensate"].expected_types["error"] is Exception

    def test_the_compensators_two_states_differ(self) -> None:
        types = ASPECT_CONTRACTS["compensate"].expected_types
        assert types["state_before"] is BaseState
        assert types["state_after"] == BaseState | None, (
            "state_after is None when the compensated aspect did not finish (runtime/saga_frame.py)"
        )


class TestTheOrders:
    """The exact orders, as `contracts/declaration-contract.md` writes them."""

    def test_summary_and_regular_share_the_base_order(self) -> None:
        base = ("self", "params", "state", "box", "connections")
        assert ASPECT_CONTRACTS["summary_aspect"].parameters == base
        assert ASPECT_CONTRACTS["regular_aspect"].parameters == base

    def test_on_error_takes_the_error_last(self) -> None:
        assert ASPECT_CONTRACTS["on_error"].parameters == (
            "self",
            "params",
            "state",
            "box",
            "connections",
            "error",
        )

    def test_compensate_takes_two_states_and_the_error(self) -> None:
        assert ASPECT_CONTRACTS["compensate"].parameters == (
            "self",
            "params",
            "state_before",
            "state_after",
            "box",
            "connections",
            "error",
        )


class TestTheReturnRules:
    """Which return each decorator promises."""

    def test_the_return_rules_are_the_declared_ones(self) -> None:
        rules = {kind: contract.return_rule for kind, contract in ASPECT_CONTRACTS.items()}
        assert rules == {
            "summary_aspect": "operation_result",
            "regular_aspect": "state_fragment",
            "on_error": "operation_result",
            "compensate": "none",
        }

    def test_no_unknown_rule_is_used(self) -> None:
        for contract in ASPECT_CONTRACTS.values():
            assert contract.return_rule in {"operation_result", "state_fragment", "none"}


class TestImmutability:
    """A contract cannot be altered after it is built."""

    def test_a_contract_is_frozen(self) -> None:
        contract = ASPECT_CONTRACTS["summary_aspect"]
        with pytest.raises(FrozenInstanceError):
            contract.kind = "regular_aspect"  # type: ignore[misc]

    def test_the_table_cannot_gain_a_kind(self) -> None:
        with pytest.raises(TypeError):
            ASPECT_CONTRACTS["invented"] = ASPECT_CONTRACTS["summary_aspect"]  # type: ignore[index]

    def test_the_type_map_cannot_be_edited(self) -> None:
        types: Any = ASPECT_CONTRACTS["compensate"].expected_types
        with pytest.raises(TypeError):
            types["error"] = str
