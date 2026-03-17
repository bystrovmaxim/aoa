"""
Тесты ReadableMixin.resolve для вложенных объектов.

Проверяем:
- Обход вложенных объектов с ReadableMixin
- Глубокую вложенность (3+ уровня)
- Навигацию по цепочке объектов
"""

from action_machine.Context.context import context
from action_machine.Context.user_info import user_info

from .conftest import make_context_with_user


class TestResolveNested:
    """Тесты resolve для вложенных объектов."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Два уровня вложенности
    # ------------------------------------------------------------------

    def test_resolve_nested_readable_mixin(self):
        """resolve обходит вложенные объекты с ReadableMixin."""
        ctx = make_context_with_user(user_id="agent_007")
        assert ctx.resolve("user.user_id") == "agent_007"

    def test_resolve_nested_roles(self):
        """Доступ к вложенному полю-списку."""
        ctx = make_context_with_user(user_id="agent_007")
        assert ctx.resolve("user.roles") == ["user", "admin"]

    # ------------------------------------------------------------------
    # ТЕСТЫ: Три уровня вложенности
    # ------------------------------------------------------------------

    def test_resolve_deep_nested(self):
        """resolve проходит по цепочке Context → UserInfo → extra (dict)."""
        ctx = make_context_with_user()
        assert ctx.resolve("user.extra.org") == "acme"

    def test_resolve_deep_nested_with_extra_dict(self):
        """resolve проходит через несколько уровней вложенных словарей."""
        user = user_info(user_id="42", extra={"level1": {"level2": {"value": "deep"}}})
        ctx = context(user=user)
        assert ctx.resolve("user.extra.level1.level2.value") == "deep"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Глубокая вложенность (3+ уровня)
    # ------------------------------------------------------------------

    def test_resolve_three_levels(self, deep_nested):
        """resolve работает с тремя уровнями вложенности."""
        result = deep_nested.resolve("level1.level2.level3.value")
        assert result == "deep"

    def test_resolve_four_levels(self):
        """resolve работает с четырьмя уровнями вложенности."""
        level4 = user_info(user_id="deep", extra={"data": {"config": {"flag": True}}})
        level3 = user_info(user_id="level3", extra={"user": level4})
        level2 = user_info(user_id="level2", extra={"next": level3})
        level1 = user_info(user_id="level1", extra={"next": level2})
        ctx = context(user=level1)

        result = ctx.resolve("user.extra.next.extra.next.extra.user.extra.data.config.flag")
        assert result is True

    # ------------------------------------------------------------------
    # ТЕСТЫ: Смешанные типы в цепочке
    # ------------------------------------------------------------------

    def test_resolve_mixed_readable_and_dict(self):
        """resolve проходит через ReadableMixin и dict в одной цепочке."""
        user = user_info(user_id="42", extra={"settings": {"theme": "dark", "notifications": {"email": True}}})
        ctx = context(user=user)

        assert ctx.resolve("user.extra.settings.theme") == "dark"
        assert ctx.resolve("user.extra.settings.notifications.email") is True

    def test_resolve_nested_with_default(self):
        """resolve с default на вложенном пути."""
        ctx = make_context_with_user()
        result = ctx.resolve("user.extra.nonexistent.deep", default="N/A")
        assert result == "N/A"
