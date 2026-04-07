# tests/domain/test_lifecycle.py
"""
Тесты для Lifecycle — декларативного конечного автомата.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет:
- Создание шаблона Lifecycle через fluent-цепочку.
- StateType enum (INITIAL, INTERMEDIATE, FINAL).
- Специализированные классы с _template.
- Экземпляры с current_state.
- Переходы (transition) и проверки (can_transition).
- Ошибки: InvalidStateError, InvalidTransitionError.
"""

import pytest

from action_machine.domain.lifecycle import (
    InvalidStateError,
    InvalidTransitionError,
    Lifecycle,
    StateType,
)


class TestLifecycleTemplate:
    """Тесты для шаблона Lifecycle (fluent-цепочка)."""

    def test_create_empty_lifecycle(self):
        """Создание пустого шаблона."""
        lifecycle = Lifecycle()
        assert len(lifecycle._states) == 0

    def test_add_state(self):
        """Добавление состояния через fluent-цепочку."""
        lifecycle = Lifecycle().state("draft", "Черновик").initial()
        assert len(lifecycle._states) == 1
        assert "draft" in lifecycle._states

    def test_state_properties(self):
        """Свойства состояния: ключ, имя, тип."""
        lifecycle = Lifecycle().state("draft", "Черновик").initial()
        state = lifecycle._states["draft"]
        assert state.key == "draft"
        assert state.display_name == "Черновик"
        assert state.state_type == StateType.INITIAL
        assert state.is_initial
        assert not state.is_final
        assert not state.is_intermediate

    def test_multiple_states(self):
        """Несколько состояний разных типов."""
        lifecycle = (
            Lifecycle()
            .state("draft", "Черновик").to("active").initial()
            .state("active", "Активный").to("archived").intermediate()
            .state("archived", "Архивирован").final()
        )
        assert len(lifecycle._states) == 3
        assert lifecycle._states["draft"].state_type == StateType.INITIAL
        assert lifecycle._states["active"].state_type == StateType.INTERMEDIATE
        assert lifecycle._states["archived"].state_type == StateType.FINAL

    def test_transitions(self):
        """Переходы между состояниями в шаблоне."""
        lifecycle = (
            Lifecycle()
            .state("draft", "Черновик").to("active", "cancelled").initial()
            .state("active", "Активный").to("archived").intermediate()
            .state("archived", "Архивирован").final()
            .state("cancelled", "Отменён").final()
        )
        transitions = lifecycle.get_transitions()
        assert transitions["draft"] == {"active", "cancelled"}
        assert transitions["active"] == {"archived"}
        assert transitions["archived"] == set()
        assert transitions["cancelled"] == set()

    def test_get_initial_keys(self):
        """Получение начальных состояний."""
        lifecycle = (
            Lifecycle()
            .state("new", "Новый").to("active").initial()
            .state("imported", "Импортирован").to("active").initial()
            .state("active", "Активный").final()
        )
        assert lifecycle.get_initial_keys() == {"new", "imported"}

    def test_get_final_keys(self):
        """Получение финальных состояний."""
        lifecycle = (
            Lifecycle()
            .state("draft", "Черновик").to("done", "cancelled").initial()
            .state("done", "Завершён").final()
            .state("cancelled", "Отменён").final()
        )
        assert lifecycle.get_final_keys() == {"done", "cancelled"}

    def test_has_state(self):
        """Проверка существования состояния."""
        lifecycle = Lifecycle().state("draft", "Черновик").initial()
        assert lifecycle.has_state("draft")
        assert not lifecycle.has_state("nonexistent")

    def test_final_state_with_transitions_raises(self):
        """Финальное состояние с переходами — ошибка."""
        with pytest.raises(ValueError, match="не может иметь переходов"):
            Lifecycle().state("done", "Завершён").to("other").final()

    def test_duplicate_state_raises(self):
        """Дублирование ключа состояния — ошибка."""
        with pytest.raises(ValueError, match="уже объявлено"):
            (
                Lifecycle()
                .state("draft", "Черновик").initial()
                .state("draft", "Дубликат").initial()
            )

    def test_uncompleted_state_raises(self):
        """Незавершённое состояние перед новым — ошибка."""
        lc = Lifecycle()
        lc.state("draft", "Черновик")  # возвращает _StateBuilder, не завершён
        with pytest.raises(RuntimeError, match="не завершено"):
            lc.state("active", "Активный")  # вызываем state() на Lifecycle, не на builder

    def test_double_finalize_raises(self):
        """Двойной вызов initial/intermediate/final — ошибка."""
        builder = Lifecycle().state("draft", "Черновик")
        builder.initial()
        with pytest.raises(RuntimeError, match="уже завершено"):
            builder.initial()


class TestSpecializedLifecycle:
    """Тесты для специализированных классов Lifecycle с _template."""

    def setup_method(self):
        """Создаёт специализированный класс для каждого теста."""

        class TestLC(Lifecycle):
            _template = (
                Lifecycle()
                .state("draft", "Черновик").to("active").initial()
                .state("active", "Активный").to("archived").intermediate()
                .state("archived", "Архивирован").final()
            )

        self.TestLC = TestLC

    def test_create_instance(self):
        """Создание экземпляра с текущим состоянием."""
        lc = self.TestLC("draft")
        assert lc.current_state == "draft"

    def test_invalid_state_raises(self):
        """Неизвестное состояние при создании — ошибка."""
        with pytest.raises(InvalidStateError, match="не объявлено"):
            self.TestLC("nonexistent")

    def test_is_initial(self):
        """Проверка is_initial."""
        lc = self.TestLC("draft")
        assert lc.is_initial
        assert not lc.is_final

    def test_is_final(self):
        """Проверка is_final."""
        lc = self.TestLC("archived")
        assert lc.is_final
        assert not lc.is_initial

    def test_available_transitions(self):
        """Доступные переходы из текущего состояния."""
        lc = self.TestLC("draft")
        assert lc.available_transitions == {"active"}

    def test_can_transition(self):
        """Проверка допустимости перехода."""
        lc = self.TestLC("draft")
        assert lc.can_transition("active")
        assert not lc.can_transition("archived")

    def test_transition(self):
        """Переход создаёт новый экземпляр."""
        lc = self.TestLC("draft")
        new_lc = lc.transition("active")

        assert new_lc.current_state == "active"
        assert lc.current_state == "draft"  # старый не изменился
        assert type(new_lc) is self.TestLC

    def test_invalid_transition_raises(self):
        """Недопустимый переход — ошибка."""
        lc = self.TestLC("draft")
        with pytest.raises(InvalidTransitionError, match="недопустим"):
            lc.transition("archived")

    def test_final_state_no_transitions(self):
        """Финальное состояние — нет доступных переходов."""
        lc = self.TestLC("archived")
        assert lc.available_transitions == set()

    def test_template_access(self):
        """Доступ к _template для координатора."""
        template = self.TestLC._get_template()
        assert template is not None
        assert len(template.get_states()) == 3
        assert template.get_initial_keys() == {"draft"}
        assert template.get_final_keys() == {"archived"}

    def test_equality(self):
        """Два экземпляра с одинаковым состоянием равны."""
        lc1 = self.TestLC("draft")
        lc2 = self.TestLC("draft")
        assert lc1 == lc2

    def test_inequality(self):
        """Два экземпляра с разным состоянием не равны."""
        lc1 = self.TestLC("draft")
        lc2 = self.TestLC("active")
        assert lc1 != lc2

    def test_hash(self):
        """Hash одинаковых экземпляров совпадает."""
        lc1 = self.TestLC("draft")
        lc2 = self.TestLC("draft")
        assert hash(lc1) == hash(lc2)
