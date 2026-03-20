# tests/aspects/test_decorators.py
"""
Тесты для новых декораторов regular_aspect и summary_aspect.
"""

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect


class TestRegularAspectDecorator:
    def test_regular_aspect_adds_meta(self):
        @regular_aspect("test description")
        def my_method():
            pass
        assert hasattr(my_method, '_new_aspect_meta')
        assert my_method._new_aspect_meta == {
            'description': 'test description',
            'type': 'regular'
        }

    def test_regular_aspect_returns_original_method(self):
        def original():
            return 42
        decorated = regular_aspect("desc")(original)
        assert decorated is original


class TestSummaryAspectDecorator:
    def test_summary_aspect_adds_meta(self):
        @summary_aspect("summary desc")
        def my_method():
            pass
        assert hasattr(my_method, '_new_aspect_meta')
        assert my_method._new_aspect_meta == {
            'description': 'summary desc',
            'type': 'summary'
        }

    def test_summary_aspect_returns_original_method(self):
        def original():
            return 42
        decorated = summary_aspect("desc")(original)
        assert decorated is original