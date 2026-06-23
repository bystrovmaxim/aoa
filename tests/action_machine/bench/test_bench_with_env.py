# tests/bench/test_bench_with_env.py
"""
Tests for ``TestBench.with_env()`` — env constant registration and resolution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Verify that ``with_env`` registers constant env values on the bench-built
context so that aspects that declare ``@context_requires("env.<key>")`` receive
the expected value during a full ``run()`` call.

``with_env`` accepts CONSTANTS only — not callables.  The lazy-provider pattern
belongs to ``@env`` on the ``Context`` class (production code).  In tests the
value is always known upfront.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    TestBench.with_env(key, value)
              |
              v   (stores EnvEntry with a _const closure in _env dict)
    TestBench._build_context()
              |
              v   (creates dynamic Context subclass with __env_entries__)
    context.resolve("env.<key>")   →  EnvEntry.get()  →  value

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``with_env`` returns a NEW bench; original is unchanged.
- ``value`` is stored as-is (not invoked, even if callable).
- Successive ``with_env`` calls merge; later call wins for the same key.
- Without ``with_env``, ``_build_context()`` returns plain ``Context`` with no
  ``__env_entries__``.

"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.env_entry import EnvEntry
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.testing import TestBench
from tests.action_machine.scenarios.domain_model.domains import SystemDomain

# ─────────────────────────────────────────────────────────────────────────────
# Minimal action that reads env values via @context_requires in the summary
# ─────────────────────────────────────────────────────────────────────────────


class _EnvResult(BaseResult):
    region: str | None
    max_retries: int | None


@meta(description="Echo env values for testing", domain=SystemDomain)
@check_roles(GuestRole)
class _EnvAction(BaseAction["_EnvAction.Params", _EnvResult]):
    class Params(BaseParams):
        pass

    @summary_aspect("Build result from env")
    @context_requires("env.region", "env.max_retries")
    async def build_env_summary(
        self,
        params: _EnvAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        ctx: Any,
    ) -> _EnvResult:
        return _EnvResult(
            region=ctx.get("env.region"),
            max_retries=ctx.get("env.max_retries"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — _build_context() resolution without a full run
# ─────────────────────────────────────────────────────────────────────────────


class TestWithEnvRegistration:
    """``with_env`` stores the constant so ``_build_context().resolve()`` returns it."""

    def test_string_constant_resolves_to_value(self) -> None:
        """String constant is stored and resolved correctly."""
        bench = TestBench().with_env("region", "eu-west-1")
        ctx = bench._build_context()

        assert ctx.resolve("env.region") == "eu-west-1"

    def test_int_constant_resolves_to_value(self) -> None:
        """Integer constant is stored and resolved correctly."""
        bench = TestBench().with_env("max_retries", 3)
        ctx = bench._build_context()

        assert ctx.resolve("env.max_retries") == 3

    def test_bool_constant_resolves_to_value(self) -> None:
        """Boolean constant is stored and resolved correctly."""
        bench = TestBench().with_env("flag", True)
        ctx = bench._build_context()

        assert ctx.resolve("env.flag") is True

    def test_none_constant_resolves_to_none(self) -> None:
        """``None`` is a valid constant — stored and resolved as ``None``."""
        bench = TestBench().with_env("opt", None)
        ctx = bench._build_context()

        assert ctx.resolve("env.opt") is None

    def test_ttl_stored_on_entry(self) -> None:
        """``ttl`` is forwarded to ``EnvEntry``."""
        bench = TestBench().with_env("flag", True, ttl=30)
        entry: EnvEntry[Any] = bench._env["flag"]

        assert entry.ttl == 30

    def test_missing_key_returns_none(self) -> None:
        """Unregistered key resolves to ``None``."""
        bench = TestBench().with_env("region", "eu-west-1")
        ctx = bench._build_context()

        assert ctx.resolve("env.other") is None

    def test_missing_key_returns_default(self) -> None:
        """Unregistered key resolves to supplied default."""
        bench = TestBench().with_env("region", "eu-west-1")
        ctx = bench._build_context()

        assert ctx.resolve("env.other", "fallback") == "fallback"

    def test_multiple_keys_all_resolve(self) -> None:
        """Multiple ``with_env`` calls register independent entries."""
        bench = TestBench().with_env("region", "eu-west-1").with_env("max_retries", 3).with_env("flag", True)
        ctx = bench._build_context()

        assert ctx.resolve("env.region") == "eu-west-1"
        assert ctx.resolve("env.max_retries") == 3
        assert ctx.resolve("env.flag") is True

    def test_later_call_overrides_same_key(self) -> None:
        """A second ``with_env`` for the same key replaces the first."""
        bench = TestBench().with_env("region", "eu-west-1").with_env("region", "ap-southeast-1")
        ctx = bench._build_context()

        assert ctx.resolve("env.region") == "ap-southeast-1"

    def test_no_env_returns_plain_context(self) -> None:
        """Without ``with_env``, ``_build_context()`` returns plain ``Context``."""
        bench = TestBench()
        ctx = bench._build_context()

        assert type(ctx) is Context  # exact type, not a dynamic subclass
        assert ctx.resolve("env.anything") is None

    def test_env_context_still_resolves_user(self) -> None:
        """Dynamic context subclass still resolves normal dot-paths."""
        bench = TestBench().with_user(user_id="u-42").with_env("region", "eu-west-1")
        ctx = bench._build_context()

        assert ctx.resolve("user.user_id") == "u-42"
        assert ctx.resolve("env.region") == "eu-west-1"


# ─────────────────────────────────────────────────────────────────────────────
# Immutability
# ─────────────────────────────────────────────────────────────────────────────


class TestWithEnvImmutability:
    """``with_env`` is immutable — returns new bench, leaves original unchanged."""

    def test_returns_new_object(self) -> None:
        bench = TestBench()
        new = bench.with_env("region", "eu-west-1")

        assert new is not bench

    def test_original_env_empty(self) -> None:
        bench = TestBench()
        bench.with_env("region", "eu-west-1")

        assert bench._env == {}

    def test_original_env_unchanged_after_override(self) -> None:
        first = TestBench().with_env("region", "eu-west-1")
        first.with_env("region", "ap-southeast-1")

        assert first._build_context().resolve("env.region") == "eu-west-1"

    def test_chain_does_not_retroactively_mutate(self) -> None:
        """Later additions don't reach earlier bench in the chain."""
        step1 = TestBench().with_env("region", "eu-west-1")
        step2 = step1.with_env("flag", True)

        assert "flag" not in step1._env
        assert "flag" in step2._env
        assert "region" in step2._env


# ─────────────────────────────────────────────────────────────────────────────
# Integration — full bench.run() with @context_requires("env.*")
# ─────────────────────────────────────────────────────────────────────────────


class TestWithEnvIntegration:
    """Env constants registered via ``with_env`` are available inside the action run."""

    @pytest.mark.anyio
    async def test_env_values_received_in_action(self, clean_bench: TestBench) -> None:
        """Action reads ``env.region`` and ``env.max_retries`` via ``ctx.get``."""
        bench = clean_bench.with_env("region", "eu-west-1").with_env("max_retries", 3)

        result = await bench.run(_EnvAction(), _EnvAction.Params(), rollup=False)

        assert result.region == "eu-west-1"
        assert result.max_retries == 3

    @pytest.mark.anyio
    async def test_env_bool_constant_in_action(self, clean_bench: TestBench) -> None:
        """Boolean env constant is received correctly in action (region is a required key too)."""
        bench = clean_bench.with_env("region", "test-eu").with_env("max_retries", 0)

        result = await bench.run(_EnvAction(), _EnvAction.Params(), rollup=False)

        assert result.region == "test-eu"
        assert result.max_retries == 0

    @pytest.mark.anyio
    async def test_env_override_reaches_action(self, clean_bench: TestBench) -> None:
        """Later ``with_env`` for the same key wins in the action."""
        bench = (
            clean_bench.with_env("region", "eu-west-1").with_env("region", "test-override").with_env("max_retries", 0)
        )

        result = await bench.run(_EnvAction(), _EnvAction.Params(), rollup=False)

        assert result.region == "test-override"
