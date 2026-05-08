# tests/bench/test_bench_immutability.py
"""
Tests that ``TestBench`` fluent helpers return new benches without mutating the original.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Verify ``with_user``, ``with_mocks``, ``with_runtime``, and ``with_request`` copy
forward bench configuration so parallel or chained tests cannot accidentally
share mutated context defaults.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    clean_bench (fixture)
              |
              +--> with_user(...)  ----->  new bench (user override)
              |
              +--> with_mocks(...) ----->  new bench (mocks override)
              |
              v
    Original bench unchanged -> _build_context() still returns stub defaults

Immutability matters for concurrent tests: a mutating ``with_user`` would make
user-specific scenarios interfere with each other.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Fluent methods return a distinct ``TestBench`` instance (not ``self``).
- Intermediate benches in a chain must not pick up later overrides.

"""

from action_machine.testing import TestBench
from tests.scenarios.domain_model.roles import AdminRole
from tests.scenarios.domain_model.services import PaymentService, PaymentServiceResource


class TestWithUser:
    """``with_user`` does not mutate the source bench."""

    def test_returns_new_object(self, clean_bench: TestBench) -> None:
        """Returns a new ``TestBench``, not the same object."""
        new = clean_bench.with_user(user_id="admin", roles=(AdminRole,))

        assert new is not clean_bench

    def test_original_user_unchanged(self, clean_bench: TestBench) -> None:
        """Original bench still exposes default ``user_id="test_user"``."""
        clean_bench.with_user(user_id="admin", roles=(AdminRole,))

        assert clean_bench._build_context().user.user_id == "test_user"

    def test_new_bench_has_new_user(self, clean_bench: TestBench) -> None:
        """Derived bench carries the overridden user and roles."""
        new = clean_bench.with_user(user_id="admin", roles=(AdminRole,))

        assert new._build_context().user.user_id == "admin"
        assert new._build_context().user.roles == (AdminRole,)


class TestWithMocks:
    """``with_mocks`` does not mutate the source bench."""

    def test_original_mocks_unchanged(self, clean_bench: TestBench) -> None:
        """Original bench keeps an empty ``mocks`` mapping."""
        clean_bench.with_mocks({PaymentServiceResource: PaymentServiceResource(PaymentService())})

        assert clean_bench.mocks == {}

    def test_new_bench_has_new_mocks(self, clean_bench: TestBench) -> None:
        """Derived bench stores the provided mocks."""
        new = clean_bench.with_mocks({PaymentServiceResource: PaymentServiceResource(PaymentService())})

        assert PaymentServiceResource in new.mocks


class TestWithRuntime:
    """``with_runtime`` does not mutate the source bench."""

    def test_original_runtime_unchanged(self, clean_bench: TestBench) -> None:
        """Original bench keeps ``hostname="test-host"``."""
        clean_bench.with_runtime(hostname="prod-01")

        assert clean_bench._build_context().runtime.hostname == "test-host"


class TestWithRequest:
    """``with_request`` does not mutate the source bench."""

    def test_original_request_unchanged(self, clean_bench: TestBench) -> None:
        """Original bench keeps ``trace_id="test-trace-000"``."""
        clean_bench.with_request(trace_id="custom")

        assert clean_bench._build_context().request.trace_id == "test-trace-000"


class TestChain:
    """Chained fluent calls compose without retroactive mutation."""

    def test_intermediate_steps_independent(self, clean_bench: TestBench) -> None:
        """Later ``with_request`` does not alter an earlier ``with_user`` bench."""
        step1 = clean_bench.with_user(user_id="step1")
        step2 = step1.with_request(trace_id="step2_trace")

        assert step1._build_context().request.trace_id == "test-trace-000"
        assert step2._build_context().request.trace_id == "step2_trace"
        assert step2._build_context().user.user_id == "step1"
