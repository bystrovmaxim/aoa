# tests/resource_managers/test_iconnection_manager.py
"""
Tests for IConnectionManager — abstract interface for transactional connections.

IConnectionManager extends BaseResourceManager with transaction lifecycle:
open(), commit(), rollback(), execute(). It supports rollup mode where commit()
calls rollback() instead of real commit. The rollup property uses getattr
with a False fallback for resilience against subclasses that skip super().__init__().

Scenarios covered:
    - Constructor sets _rollup attribute.
    - rollup property returns True when rollup=True.
    - rollup property returns False when rollup=False (default).
    - rollup property returns False when _rollup not set (no super().__init__).
    - check_rollup_support() always returns True.
    - commit() calls rollback() when rollup=True.
    - commit() does NOT call rollback() when rollup=False.
    - Abstract methods (open, rollback, execute) must be implemented.
    - Subclass with rollup=True — commit delegates to rollback.
"""


import pytest

from action_machine.resource_managers.iconnection_manager import IConnectionManager

# ─────────────────────────────────────────────────────────────────────────────
# Concrete subclass for testing — IConnectionManager is abstract.
# ─────────────────────────────────────────────────────────────────────────────


class _TestConnectionManager(IConnectionManager):
    """Minimal concrete implementation for testing IConnectionManager behavior."""

    def __init__(self, rollup: bool = False) -> None:
        super().__init__(rollup=rollup)
        self.opened = False
        self.rolled_back = False
        self.committed = False
        self.executed_queries: list[str] = []

    def get_wrapper_class(self):
        return None

    async def open(self) -> None:
        self.opened = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def execute(self, query: str, params=None):
        self.executed_queries.append(query)
        return None

    async def commit(self) -> None:
        """Commit that respects rollup via super().commit()."""
        if self.rollup:
            await self.rollback()
            return
        self.committed = True


class _NoSuperInitManager(IConnectionManager):
    """Subclass that intentionally skips super().__init__()."""

    def __init__(self) -> None:
        # Intentionally NOT calling super().__init__()
        pass

    def get_wrapper_class(self):
        return None

    async def open(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, query: str, params=None):
        return None


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
    """Verify that IConnectionManager always supports rollup."""

    def test_returns_true(self) -> None:
        """check_rollup_support() returns True for any IConnectionManager."""
        mgr = _TestConnectionManager()
        assert mgr.check_rollup_support() is True

    def test_returns_true_with_rollup_active(self) -> None:
        """check_rollup_support() returns True even when rollup is active."""
        mgr = _TestConnectionManager(rollup=True)
        assert mgr.check_rollup_support() is True

    def test_returns_true_without_super_init(self) -> None:
        """check_rollup_support() returns True even without super().__init__."""
        mgr = _NoSuperInitManager()
        assert mgr.check_rollup_support() is True


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
        """IConnectionManager.commit() itself calls rollback when rollup=True."""
        mgr = _TestConnectionManager(rollup=True)

        # Call the base class commit directly
        await IConnectionManager.commit(mgr)

        assert mgr.rolled_back is True


# ═════════════════════════════════════════════════════════════════════════════
# Abstract method enforcement
# ═════════════════════════════════════════════════════════════════════════════


class TestAbstractMethods:
    """Verify that abstract methods must be implemented."""

    def test_cannot_instantiate_without_open(self) -> None:
        """Subclass missing open() cannot be instantiated."""

        class _Incomplete(IConnectionManager):
            def get_wrapper_class(self):
                return None

            async def rollback(self):
                pass

            async def execute(self, query, params=None):
                pass

        with pytest.raises(TypeError):
            _Incomplete()

    def test_cannot_instantiate_without_rollback(self) -> None:
        """Subclass missing rollback() cannot be instantiated."""

        class _Incomplete(IConnectionManager):
            def get_wrapper_class(self):
                return None

            async def open(self):
                pass

            async def execute(self, query, params=None):
                pass

        with pytest.raises(TypeError):
            _Incomplete()

    def test_cannot_instantiate_without_execute(self) -> None:
        """Subclass missing execute() cannot be instantiated."""

        class _Incomplete(IConnectionManager):
            def get_wrapper_class(self):
                return None

            async def open(self):
                pass

            async def rollback(self):
                pass

        with pytest.raises(TypeError):
            _Incomplete()


# ═════════════════════════════════════════════════════════════════════════════
# Full lifecycle
# ═════════════════════════════════════════════════════════════════════════════


class TestFullLifecycle:
    """Verify open → execute → commit/rollback lifecycle."""

    @pytest.mark.asyncio
    async def test_normal_lifecycle(self) -> None:
        """open → execute → commit works in non-rollup mode."""
        mgr = _TestConnectionManager(rollup=False)

        await mgr.open()
        await mgr.execute("INSERT INTO t VALUES (1)")
        await mgr.commit()

        assert mgr.opened is True
        assert mgr.executed_queries == ["INSERT INTO t VALUES (1)"]
        assert mgr.committed is True
        assert mgr.rolled_back is False

    @pytest.mark.asyncio
    async def test_rollup_lifecycle(self) -> None:
        """open → execute → commit (rollup=True) rolls back instead."""
        mgr = _TestConnectionManager(rollup=True)

        await mgr.open()
        await mgr.execute("INSERT INTO t VALUES (1)")
        await mgr.commit()

        assert mgr.opened is True
        assert mgr.executed_queries == ["INSERT INTO t VALUES (1)"]
        assert mgr.committed is False
        assert mgr.rolled_back is True

    @pytest.mark.asyncio
    async def test_explicit_rollback(self) -> None:
        """Explicit rollback works regardless of rollup flag."""
        mgr = _TestConnectionManager(rollup=False)

        await mgr.open()
        await mgr.execute("INSERT INTO t VALUES (1)")
        await mgr.rollback()

        assert mgr.rolled_back is True
        assert mgr.committed is False
