# tests/aspects/test_aspect_gate_host.py
"""
Тесты для AspectGateHost — миксина, который присоединяет AspectGate к классу действия.

Проверяем:
- Сбор обычных аспектов (методы, декорированные @regular_aspect)
- Сбор summary-аспекта (метод, декорированный @summary_aspect)
- Ошибку, если есть регулярные аспекты, но нет summary (при создании экземпляра)
- Ошибку, если объявлено два summary-аспекта
- Отсутствие наследования аспектов (каждый класс определяет свои)
- Удаление временных метаданных после сборки
- Отсутствие методов для модификации аспектов на уровне экземпляра
- Кэширование аспектов на уровне класса (все экземпляры разделяют данные)
"""

import pytest

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Core.ToolsBox import ToolsBox


class TestAspectGateHost:
    """Тесты для AspectGateHost."""

    # ------------------------------------------------------------------
    # Базовый сбор аспектов
    # ------------------------------------------------------------------
    def test_instances_share_aspect_data(self):
        """Все экземпляры одного класса возвращают одинаковые данные аспектов (кэш)."""
        class MyAction(AspectGateHost):
            @regular_aspect("shared")
            async def shared(self, params, state, box: ToolsBox, connections):
                pass
            @summary_aspect("shared_summary")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        action1 = MyAction()
        action2 = MyAction()

        reg1, sum1 = action1.get_aspects()
        reg2, sum2 = action2.get_aspects()

        # Кэш на уровне класса, поэтому объекты списка и кортежа должны совпадать
        assert reg1 is reg2
        assert sum1 is sum2
        assert len(reg1) == 1
        assert reg1[0][0].__name__ == "shared"
        assert reg1[0][1] == "shared"
        assert sum1[0].__name__ == "summ"
        assert sum1[1] == "shared_summary"

    def test_get_aspects_empty(self):
        """Действие только с summary-аспектом возвращает пустой список регулярных."""
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        action = MyAction()
        regular, summary = action.get_aspects()
        assert regular == []
        assert summary is not None
        assert summary[0].__name__ == "summ"
        assert summary[1] == "test"

    def test_get_aspects_with_regular_and_summary(self):
        """Действие с регулярными и summary-аспектом возвращает корректные списки."""
        class MyAction(AspectGateHost):
            @regular_aspect("first")
            async def first(self, params, state, box: ToolsBox, connections):
                pass

            @regular_aspect("second")
            async def second(self, params, state, box: ToolsBox, connections):
                pass

            @summary_aspect("summary")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        action = MyAction()
        regular, summary = action.get_aspects()
        assert len(regular) == 2
        assert regular[0][0].__name__ == "first"
        assert regular[0][1] == "first"
        assert regular[1][0].__name__ == "second"
        assert regular[1][1] == "second"
        assert summary is not None
        assert summary[0].__name__ == "summ"
        assert summary[1] == "summary"

    # ------------------------------------------------------------------
    # Обработка ошибок
    # ------------------------------------------------------------------
    def test_missing_summary_raises_on_instance_creation(self):
        """
        Действие с регулярными аспектами, но без summary-аспекта,
        вызывает TypeError при создании экземпляра.
        """
        class MyAction(AspectGateHost):
            @regular_aspect("only")
            async def only(self, params, state, box: ToolsBox, connections):
                pass

        with pytest.raises(TypeError, match="does not have a summary aspect"):
            MyAction()  # создание экземпляра вызывает проверку в __init__

    def test_duplicate_summary_in_single_class_raises(self):
        """Нельзя определить два summary-аспекта в одном классе."""
        with pytest.raises(TypeError, match="Only one summary aspect can be registered per action"):
            class MyAction(AspectGateHost):
                @summary_aspect("first")
                async def summ1(self, params, state, box: ToolsBox, connections):
                    pass

                @summary_aspect("second")
                async def summ2(self, params, state, box: ToolsBox, connections):
                    pass

    # ------------------------------------------------------------------
    # Наследование (аспекты не наследуются)
    # ------------------------------------------------------------------
    def test_child_must_have_own_summary(self):
        """
        Дочерний класс не наследует summary-аспект от родителя;
        если у ребёнка есть регулярные аспекты, но нет summary — ошибка.
        """
        class Parent(AspectGateHost):
            @summary_aspect("parent_summary")
            async def parent_summary(self, params, state, box: ToolsBox, connections):
                pass

        # Ребёнок добавляет регулярный аспект, но не добавляет summary — ошибка
        with pytest.raises(TypeError, match="does not have a summary aspect"):
            class Child(Parent):
                @regular_aspect("child")
                async def child_aspect(self, params, state, box: ToolsBox, connections):
                    pass

            Child()  # создание экземпляра вызывает ошибку

    def test_inheritance_does_not_copy_aspects(self):
        """
        Аспекты родителя не копируются в ребёнка.
        Каждый класс определяет свои аспекты независимо.
        """
        class Parent(AspectGateHost):
            @regular_aspect("parent_regular")
            async def parent_reg(self, params, state, box: ToolsBox, connections):
                pass
            @summary_aspect("parent_summary")
            async def parent_summary(self, params, state, box: ToolsBox, connections):
                pass

        class Child(Parent):
            @regular_aspect("child_regular")
            async def child_reg(self, params, state, box: ToolsBox, connections):
                pass
            @summary_aspect("child_summary")
            async def child_summary(self, params, state, box: ToolsBox, connections):
                pass

        parent = Parent()
        child = Child()

        parent_reg, parent_sum = parent.get_aspects()
        child_reg, child_sum = child.get_aspects()

        # У родителя только его аспекты
        assert len(parent_reg) == 1
        assert parent_reg[0][0].__name__ == "parent_reg"
        assert parent_sum[0].__name__ == "parent_summary"

        # У ребёнка только его аспекты (родительские не копируются)
        assert len(child_reg) == 1
        assert child_reg[0][0].__name__ == "child_reg"
        assert child_sum[0].__name__ == "child_summary"

    # ------------------------------------------------------------------
    # Удаление временных метаданных
    # ------------------------------------------------------------------
    def test_temporary_meta_removed_after_class_creation(self):
        """
        После создания класса временный атрибут _new_aspect_meta,
        добавленный декораторами, удаляется.
        """
        class MyAction(AspectGateHost):
            @regular_aspect("test")
            async def test(self, params, state, box: ToolsBox, connections):
                pass

            @summary_aspect("summary")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        assert not hasattr(MyAction.test, '_new_aspect_meta')
        assert not hasattr(MyAction.summ, '_new_aspect_meta')

    # ------------------------------------------------------------------
    # Отсутствие методов для модификации на уровне экземпляра
    # ------------------------------------------------------------------
    def test_no_per_instance_modification_methods(self):
        """
        Методы, которые позволяли изменять аспекты на уровне экземпляра,
        должны отсутствовать. Все аспекты определяются на уровне класса.
        """
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        action = MyAction()

        # Убеждаемся, что методов для изменения аспектов на уровне экземпляра нет
        assert not hasattr(action, 'add_regular_aspect')
        assert not hasattr(action, 'remove_regular_aspect')
        assert not hasattr(action, 'set_summary_aspect')
        assert not hasattr(action, 'remove_summary_aspect')
        assert not hasattr(action, '_ensure_copy')
        assert not hasattr(action, '_instance_gate')