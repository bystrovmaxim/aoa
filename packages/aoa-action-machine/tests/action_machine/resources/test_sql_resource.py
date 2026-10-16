# tests/resources/test_sql_resource.py
"""
Tests for SqlResource — abstract base for transactional SQL connections.

SqlResource extends BaseResource with the transaction lifecycle:
open(), begin(), commit(), rollback(), close(). It supports rollup mode where commit()
calls rollback() instead of real commit. The rollup property uses getattr
with a False fallback for resilience against subclasses that skip super().__init__().

There is no query member in this contract: a subclass implements open(), begin()
and rollback() and nothing else, and the driver keeps its own protected helpers
for the statements its domain methods run.

Scenarios covered:
    - Constructor sets _rollup attribute.
    - rollup property returns True when rollup=True.
    - rollup property returns False when rollup=False (default).
    - rollup property returns False when _rollup not set (no super().__init__).
    - check_rollup_support() always returns True.
    - commit() calls rollback() when rollup=True.
    - commit() does NOT call rollback() when rollup=False.
    - Abstract methods (open, begin, rollback) must be implemented.
    - No query member on the contract, the base or the proxy.
    - A subclass implementing the three abstract methods is concrete.
    - Subclass with rollup=True — commit delegates to rollback.
"""


import pytest

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.resources.sql import ProtocolSqlResource, SqlResource, WrapperSqlResource


class _SqlResourceTestDomain(BaseDomain):
    name = "sql_resource_test"
    description = "Domain for SQL resource-layer tests."


def meta(description: str, domain: type[BaseDomain]):
    """Test-local metadata decorator matching the graph metadata contract."""

    def decorator(cls):
        cls._meta_info = {"description": description, "domain": domain}
        return cls

    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# Concrete subclass for testing — SqlResource is abstract.
# ─────────────────────────────────────────────────────────────────────────────


@meta(description="SQL resource test connection manager", domain=_SqlResourceTestDomain)
class _TestConnectionManager(SqlResource):
    """Minimal concrete implementation for testing SqlResource behavior."""

    def __init__(self, rollup: bool = False) -> None:
        super().__init__(rollup=rollup)
        self.opened = False
        self.begun = False
        self.rolled_back = False
        self.committed = False

    def get_wrapper_class(self):
        return None

    async def open(self) -> None:
        self.opened = True

    async def begin(self) -> None:
        self.begun = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def commit(self) -> None:
        """Commit that respects rollup via super().commit()."""
        if self.rollup:
            await self.rollback()
            return
        self.committed = True


@meta(description="SQL resource test manager without super init", domain=_SqlResourceTestDomain)
class _NoSuperInitManager(SqlResource):
    """Subclass that intentionally skips super().__init__()."""

    def __init__(self) -> None:
        # Intentionally NOT calling super().__init__()
        pass

    def get_wrapper_class(self):
        return None

    async def open(self) -> None:
        pass

    async def begin(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


# ═════════════════════════════════════════════════════════════════════════════
# Constructor and rollup property
# ═════════════════════════════════════════════════════════════════════════════


class TestRollupProperty:
    """Verify rollup flag storage and property behavior."""

    def test_default_rollup_false(self) -> None:
        """Default rollup is False."""
        mgr = _TestConnectionManager()
        assert mgr.rollup is False

    def test_rollup_true(self) -> None:
        """Passing rollup=True stores and returns True."""
        mgr = _TestConnectionManager(rollup=True)
        assert mgr.rollup is True

    def test_rollup_false_explicit(self) -> None:
        """Explicitly passing rollup=False returns False."""
        mgr = _TestConnectionManager(rollup=False)
        assert mgr.rollup is False

    def test_rollup_fallback_without_super_init(self) -> None:
        """When _rollup is not set (no super().__init__), rollup returns False."""
        mgr = _NoSuperInitManager()
        assert mgr.rollup is False


# ═════════════════════════════════════════════════════════════════════════════
# check_rollup_support
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckRollupSupport:
    """Verify that SqlResource always supports rollup."""

    @pytest.mark.asyncio
    async def test_returns_true(self) -> None:
        """check_rollup_support() returns True for any SqlResource."""
        mgr = _TestConnectionManager()
        assert await mgr.check_rollup_support() is True

    @pytest.mark.asyncio
    async def test_returns_true_with_rollup_active(self) -> None:
        """check_rollup_support() returns True even when rollup is active."""
        mgr = _TestConnectionManager(rollup=True)
        assert await mgr.check_rollup_support() is True

    @pytest.mark.asyncio
    async def test_returns_true_without_super_init(self) -> None:
        """check_rollup_support() returns True even without super().__init__."""
        mgr = _NoSuperInitManager()
        assert await mgr.check_rollup_support() is True


# ═════════════════════════════════════════════════════════════════════════════
# commit() behavior with rollup
# ═════════════════════════════════════════════════════════════════════════════


class TestCommitRollup:
    """Verify commit() delegates to rollback() when rollup=True."""

    @pytest.mark.asyncio
    async def test_commit_with_rollup_calls_rollback(self) -> None:
        """When rollup=True, commit() calls rollback() instead of committing."""
        mgr = _TestConnectionManager(rollup=True)

        await mgr.commit()

        assert mgr.rolled_back is True
        assert mgr.committed is False

    @pytest.mark.asyncio
    async def test_commit_without_rollup_does_not_rollback(self) -> None:
        """When rollup=False, commit() performs a real commit."""
        mgr = _TestConnectionManager(rollup=False)

        await mgr.commit()

        assert mgr.committed is True
        assert mgr.rolled_back is False

    @pytest.mark.asyncio
    async def test_base_commit_with_rollup(self) -> None:
        """SqlResource.commit() itself calls rollback when rollup=True."""
        mgr = _TestConnectionManager(rollup=True)

        # Call the base class commit directly
        await SqlResource.commit(mgr)

        assert mgr.rolled_back is True


# ═════════════════════════════════════════════════════════════════════════════
# Abstract method enforcement
# ═════════════════════════════════════════════════════════════════════════════


class TestAbstractMethods:
    """Verify that abstract methods must be implemented."""

    def test_cannot_instantiate_without_open(self) -> None:
        """Subclass missing open() cannot be instantiated."""

        @meta(description="Incomplete SQL resource missing open", domain=_SqlResourceTestDomain)
        class _Incomplete(SqlResource):
            def get_wrapper_class(self):
                return None

            async def begin(self):
                pass

            async def rollback(self):
                pass

        with pytest.raises(TypeError):
            _Incomplete()

    def test_cannot_instantiate_without_begin(self) -> None:
        """Subclass missing begin() cannot be instantiated."""

        @meta(description="Incomplete SQL resource missing begin", domain=_SqlResourceTestDomain)
        class _Incomplete(SqlResource):
            def get_wrapper_class(self):
                return None

            async def open(self):
                pass

            async def rollback(self):
                pass

        with pytest.raises(TypeError):
            _Incomplete()

    def test_cannot_instantiate_without_rollback(self) -> None:
        """Subclass missing rollback() cannot be instantiated."""

        @meta(description="Incomplete SQL resource missing rollback", domain=_SqlResourceTestDomain)
        class _Incomplete(SqlResource):
            def get_wrapper_class(self):
                return None

            async def open(self):
                pass

            async def begin(self):
                pass

        with pytest.raises(TypeError):
            _Incomplete()

    def test_a_subclass_with_the_three_abstract_members_is_concrete(self) -> None:
        """open, begin and rollback are the whole obligation; commit comes from the base (FR-004)."""

        @meta(description="SQL resource with the three abstract members", domain=_SqlResourceTestDomain)
        class _Complete(SqlResource):
            def get_wrapper_class(self):
                return None

            async def open(self):
                pass

            async def begin(self):
                pass

            async def rollback(self):
                pass

        assert _Complete.__abstractmethods__ == frozenset()


# ═════════════════════════════════════════════════════════════════════════════
# No query member anywhere in the contract (FR-001 … FR-004)
# ═════════════════════════════════════════════════════════════════════════════


class TestNoQueryMember:
    """The query surface left the contract: what remains is the lifecycle and rollup."""

    def test_no_shape_exposes_a_query_member(self) -> None:
        """The contract, the base and the proxy expose no passthrough at all."""
        for shape in (ProtocolSqlResource, SqlResource, WrapperSqlResource):
            assert not hasattr(shape, "execute"), shape

    def test_the_proxy_exposes_no_protected_helper_either(self) -> None:
        """The driver's helpers are the driver's; a nested action cannot reach them through the proxy."""
        for protected in ("_execute", "_fetchrow", "_require_connection"):
            assert not hasattr(WrapperSqlResource, protected), protected


# ═════════════════════════════════════════════════════════════════════════════
# Full lifecycle
# ═════════════════════════════════════════════════════════════════════════════


class TestFullLifecycle:
    """Verify the open → begin → commit/rollback lifecycle."""

    @pytest.mark.asyncio
    async def test_normal_lifecycle(self) -> None:
        """open → begin → commit works in non-rollup mode."""
        mgr = _TestConnectionManager(rollup=False)

        await mgr.open()
        await mgr.begin()
        await mgr.commit()

        assert mgr.opened is True
        assert mgr.begun is True
        assert mgr.committed is True
        assert mgr.rolled_back is False

    @pytest.mark.asyncio
    async def test_rollup_lifecycle(self) -> None:
        """open → begin → commit (rollup=True) rolls back instead."""
        mgr = _TestConnectionManager(rollup=True)

        await mgr.open()
        await mgr.begin()
        await mgr.commit()

        assert mgr.opened is True
        assert mgr.begun is True
        assert mgr.committed is False
        assert mgr.rolled_back is True

    @pytest.mark.asyncio
    async def test_explicit_rollback(self) -> None:
        """Explicit rollback works regardless of rollup flag."""
        mgr = _TestConnectionManager(rollup=False)

        await mgr.open()
        await mgr.begin()
        await mgr.rollback()

        assert mgr.rolled_back is True
        assert mgr.committed is False


# ═════════════════════════════════════════════════════════════════════════════
# Closing: a concrete harmless default (FR-006, FR-023)
# ═════════════════════════════════════════════════════════════════════════════


class TestCloseDefault:
    """``close()`` is part of the contract with a body, so no subclass is obliged to write one."""

    @pytest.mark.anyio
    async def test_a_manager_holding_nothing_closes_harmlessly(self) -> None:
        """The subclass below never mentions close, and that is enough."""
        manager = _TestConnectionManager()

        assert await manager.close() is None
        assert await manager.close() is None  # a second close is just as harmless

    @pytest.mark.anyio
    async def test_the_double_that_skips_super_init_also_closes(self) -> None:
        """The default does not depend on ``_rollup`` or on ``super().__init__()``."""
        assert await _NoSuperInitManager().close() is None

    def test_close_is_not_abstract(self) -> None:
        """A subclass that omits it stays concrete — that is what keeps the stubs unedited."""
        assert _TestConnectionManager.__abstractmethods__ == frozenset()
