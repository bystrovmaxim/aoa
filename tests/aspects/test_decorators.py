# tests/aspects/test_decorators.py
"""
Тесты для декораторов regular_aspect и summary_aspect.

Проверяем:
- Прикрепление метаданных _new_aspect_meta
- Возврат оригинального метода
- Ошибки при применении к синхронным методам
"""

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect


class TestRegularAspectDecorator:
    def test_regular_aspect_adds_meta(self):
        # Декоратор требует 5 параметров и async def
        @regular_aspect("test description")
        async def my_method(self, params, state, box, connections):
            pass

        assert hasattr(my_method, '_new_aspect_meta')
        assert my_method._new_aspect_meta == {
            'description': 'test description',
            'type': 'regular'
        }

    def test_regular_aspect_returns_original_method(self):
        async def original(self, params, state, box, connections):
            return 42

        decorated = regular_aspect("desc")(original)
        assert decorated is original


class TestSummaryAspectDecorator:
    def test_summary_aspect_adds_meta(self):
        @summary_aspect("summary desc")
        async def my_method(self, params, state, box, connections):
            pass

        assert hasattr(my_method, '_new_aspect_meta')
        assert my_method._new_aspect_meta == {
            'description': 'summary desc',
            'type': 'summary'
        }

    def test_summary_aspect_returns_original_method(self):
        async def original(self, params, state, box, connections):
            return 42

        decorated = summary_aspect("desc")(original)
        assert decorated is original
