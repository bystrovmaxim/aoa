# tests/action_machine/intents/checkers/test_checker_opaque.py
"""Unit tests for opaque=True support across all result_* checker decorators."""


from aoa.action_machine.intents.checkers.result_bool_decorator import FieldBoolChecker, result_bool
from aoa.action_machine.intents.checkers.result_date_decorator import FieldDateChecker, result_date
from aoa.action_machine.intents.checkers.result_float_decorator import FieldFloatChecker, result_float
from aoa.action_machine.intents.checkers.result_instance_decorator import FieldInstanceChecker, result_instance
from aoa.action_machine.intents.checkers.result_int_decorator import FieldIntChecker, result_int
from aoa.action_machine.intents.checkers.result_string_decorator import FieldStringChecker, result_string

# ═════════════════════════════════════════════════════════════════════════════
# result_string
# ═════════════════════════════════════════════════════════════════════════════


class TestResultStringOpaque:
    def test_default_opaque_false(self) -> None:
        checker = FieldStringChecker("name")
        assert checker.opaque is False

    def test_opaque_true_stored(self) -> None:
        checker = FieldStringChecker("name", opaque=True)
        assert checker.opaque is True

    def test_decorator_meta_opaque_default(self) -> None:
        @result_string("name")
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is False

    def test_decorator_meta_opaque_true(self) -> None:
        @result_string("name", opaque=True)
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is True


# ═════════════════════════════════════════════════════════════════════════════
# result_int
# ═════════════════════════════════════════════════════════════════════════════


class TestResultIntOpaque:
    def test_default_opaque_false(self) -> None:
        checker = FieldIntChecker("count")
        assert checker.opaque is False

    def test_opaque_true_stored(self) -> None:
        checker = FieldIntChecker("count", opaque=True)
        assert checker.opaque is True

    def test_decorator_meta_opaque_default(self) -> None:
        @result_int("count")
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is False

    def test_decorator_meta_opaque_true(self) -> None:
        @result_int("count", opaque=True)
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is True


# ═════════════════════════════════════════════════════════════════════════════
# result_float
# ═════════════════════════════════════════════════════════════════════════════


class TestResultFloatOpaque:
    def test_default_opaque_false(self) -> None:
        checker = FieldFloatChecker("price")
        assert checker.opaque is False

    def test_opaque_true_stored(self) -> None:
        checker = FieldFloatChecker("price", opaque=True)
        assert checker.opaque is True

    def test_decorator_meta_opaque_default(self) -> None:
        @result_float("price")
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is False

    def test_decorator_meta_opaque_true(self) -> None:
        @result_float("price", opaque=True)
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is True


# ═════════════════════════════════════════════════════════════════════════════
# result_bool
# ═════════════════════════════════════════════════════════════════════════════


class TestResultBoolOpaque:
    def test_default_opaque_false(self) -> None:
        checker = FieldBoolChecker("flag")
        assert checker.opaque is False

    def test_opaque_true_stored(self) -> None:
        checker = FieldBoolChecker("flag", opaque=True)
        assert checker.opaque is True

    def test_decorator_meta_opaque_default(self) -> None:
        @result_bool("flag")
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is False

    def test_decorator_meta_opaque_true(self) -> None:
        @result_bool("flag", opaque=True)
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is True


# ═════════════════════════════════════════════════════════════════════════════
# result_date
# ═════════════════════════════════════════════════════════════════════════════


class TestResultDateOpaque:
    def test_default_opaque_false(self) -> None:
        checker = FieldDateChecker("created_at")
        assert checker.opaque is False

    def test_opaque_true_stored(self) -> None:
        checker = FieldDateChecker("created_at", opaque=True)
        assert checker.opaque is True

    def test_decorator_meta_opaque_default(self) -> None:
        @result_date("created_at")
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is False

    def test_decorator_meta_opaque_true(self) -> None:
        @result_date("created_at", opaque=True)
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is True


# ═════════════════════════════════════════════════════════════════════════════
# result_instance
# ═════════════════════════════════════════════════════════════════════════════


class _SomeDomainObj:
    pass


class TestResultInstanceOpaque:
    def test_default_opaque_false(self) -> None:
        checker = FieldInstanceChecker("obj", _SomeDomainObj)
        assert checker.opaque is False

    def test_opaque_true_stored(self) -> None:
        checker = FieldInstanceChecker("obj", _SomeDomainObj, opaque=True)
        assert checker.opaque is True

    def test_decorator_meta_opaque_default(self) -> None:
        @result_instance("obj", _SomeDomainObj)
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is False

    def test_decorator_meta_opaque_true(self) -> None:
        @result_instance("obj", _SomeDomainObj, opaque=True)
        def aspect():
            pass

        assert aspect._checker_meta[0]["opaque"] is True
