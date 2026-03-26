# tests/checkers/test_result_checkers.py
from datetime import datetime

import pytest

from action_machine.Checkers.ResultBoolChecker import ResultBoolChecker
from action_machine.Checkers.ResultDateChecker import ResultDateChecker
from action_machine.Checkers.ResultFloatChecker import ResultFloatChecker
from action_machine.Checkers.ResultInstanceChecker import ResultInstanceChecker
from action_machine.Checkers.ResultIntChecker import ResultIntChecker
from action_machine.Checkers.ResultStringChecker import ResultStringChecker
from action_machine.Core.Exceptions import ValidationFieldError


class DummyClass: pass
class OtherClass: pass

class TestResultCheckersCoverage:
    def test_bool(self):
        checker = ResultBoolChecker("f", "desc")
        checker.check({"f": True})
        with pytest.raises(ValidationFieldError, match="должен быть булевым"):
            checker.check({"f": 123})

    def test_date(self):
        checker = ResultDateChecker("d", "desc", format="%Y-%m-%d", min_date=datetime(2020, 1, 1), max_date=datetime(2025, 1, 1))
        checker.check({"d": "2023-01-01"})
        checker.check({"d": datetime(2023, 1, 1)})

        with pytest.raises(ValidationFieldError, match="требуется указать формат"):
            ResultDateChecker("d", "desc").check({"d": "2023-01-01"})
        with pytest.raises(ValidationFieldError, match="соответствующей формату"):
            checker.check({"d": "invalid"})
        with pytest.raises(ValidationFieldError, match="не меньше"):
            checker.check({"d": datetime(2019, 1, 1)})
        with pytest.raises(ValidationFieldError, match="не больше"):
            checker.check({"d": datetime(2026, 1, 1)})
        with pytest.raises(ValidationFieldError, match="должен быть объектом datetime или строкой"):
            checker.check({"d": 123})

    def test_float(self):
        checker = ResultFloatChecker("f", "desc", min_value=1.0, max_value=5.0)
        checker.check({"f": 3.0})
        checker.check({"f": 3})

        with pytest.raises(ValidationFieldError, match="должно быть числом"):
            checker.check({"f": "3.0"})
        with pytest.raises(ValidationFieldError, match="не меньше"):
            checker.check({"f": 0.5})
        with pytest.raises(ValidationFieldError, match="не больше"):
            checker.check({"f": 6.0})

    def test_int(self):
        checker = ResultIntChecker("i", "desc", min_value=1, max_value=5)
        checker.check({"i": 3})

        with pytest.raises(ValidationFieldError, match="должен быть целым числом"):
            checker.check({"i": 3.5})
        with pytest.raises(ValidationFieldError, match="не меньше"):
            checker.check({"i": 0})
        with pytest.raises(ValidationFieldError, match="не больше"):
            checker.check({"i": 6})

    def test_string(self):
        checker = ResultStringChecker("s", "desc", min_length=2, max_length=5, not_empty=True)
        checker.check({"s": "abc"})

        with pytest.raises(ValidationFieldError, match="должен быть строкой"):
            checker.check({"s": 123})
        with pytest.raises(ValidationFieldError, match="не может быть пустым"):
            checker.check({"s": ""})
        with pytest.raises(ValidationFieldError, match="не меньше"):
            checker.check({"s": "a"})
        with pytest.raises(ValidationFieldError, match="не больше"):
            checker.check({"s": "abcdef"})

    def test_instance(self):
        c1 = ResultInstanceChecker("obj", DummyClass, "desc")
        c1.check({"obj": DummyClass()})
        with pytest.raises(ValidationFieldError, match="должно быть экземпляром класса DummyClass"):
            c1.check({"obj": OtherClass()})

        c2 = ResultInstanceChecker("obj", (DummyClass, OtherClass), "desc")
        c2.check({"obj": OtherClass()})
        with pytest.raises(ValidationFieldError, match="одного из классов"):
            c2.check({"obj": 123})
