"""
Тесты кеширования результатов в ReadableMixin.resolve.

Проверяем:
- Кеширование успешных результатов
- Кеширование default для отсутствующих путей
- Поведение кеша при повторных вызовах
"""

from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo


class TestResolveCaching:
    """Тесты кеширования результатов resolve."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Кеширование успешных результатов
    # ------------------------------------------------------------------

    def test_resolve_caches_result(self):
        """resolve кеширует результат при повторном вызове."""
        user = UserInfo(user_id="42")

        # Первый вызов
        result1 = user.resolve("user_id")
        assert result1 == "42"

        # Проверяем что кеш существует и содержит ключ
        assert "user_id" in user._resolve_cache
        assert user._resolve_cache["user_id"] == "42"

        # Второй вызов
        result2 = user.resolve("user_id")
        assert result2 == "42"

    def test_resolve_cache_returns_same_object(self):
        """Кеш возвращает тот же объект, не копию."""
        user = UserInfo(extra={"data": [1, 2, 3]})

        result1 = user.resolve("extra.data")
        result2 = user.resolve("extra.data")

        # Должен быть тот же список (по id)
        assert result1 is result2
        assert id(result1) == id(result2)

    def test_resolve_cache_hit_returns_cached_value(self):
        """
        resolve при повторном вызове возвращает закешированное значение,
        даже если оригинальное значение изменилось.

        Это демонстрирует, что кеш не инвалидируется при изменении объекта.
        """
        user = UserInfo(user_id="42", extra={"key": "value"})

        # Первый вызов — заполняем кеш
        result1 = user.resolve("extra.key")
        assert result1 == "value"

        # Меняем значение в объекте (в реальности так не надо делать,
        # но для теста — чтобы проверить кеш)
        user.extra["key"] = "changed"

        # Второй вызов — должен вернуть закешированное старое значение
        result2 = user.resolve("extra.key")
        assert result2 == "value"  # не "changed", потому что из кеша

    # ------------------------------------------------------------------
    # ТЕСТЫ: Кеширование default
    # ------------------------------------------------------------------

    def test_resolve_caches_default_for_missing(self):
        """resolve кеширует default для несуществующего пути."""
        user = UserInfo(user_id="42")

        # Первый вызов с default
        result = user.resolve("missing", default="fallback")
        assert result == "fallback"

        # Проверяем что в кеше сохранился default
        assert user._resolve_cache["missing"] == "fallback"

        # Второй вызов — должен вернуть закешированный default
        result2 = user.resolve("missing", default="other")
        assert result2 == "fallback"  # не "other"

    def test_resolve_caches_none_for_missing(self):
        """resolve кеширует None для несуществующего пути без default."""
        user = UserInfo(user_id="42")

        # Первый вызов
        result = user.resolve("missing")
        assert result is None

        # Проверяем кеш
        assert user._resolve_cache["missing"] is None

        # Второй вызов с default — должен вернуть закешированный None,
        # а не default
        result2 = user.resolve("missing", default="fallback")
        assert result2 is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: Независимость кеша для разных путей
    # ------------------------------------------------------------------

    def test_cache_independent_for_different_paths(self):
        """Кеш для разных путей независим."""
        user = UserInfo(user_id="42", extra={"org": "acme"})

        # Заполняем кеш для двух путей
        user.resolve("user_id")
        user.resolve("extra.org")

        # Проверяем что оба значения в кеше
        assert "user_id" in user._resolve_cache
        assert "extra.org" in user._resolve_cache
        assert user._resolve_cache["user_id"] == "42"
        assert user._resolve_cache["extra.org"] == "acme"

    def test_cache_for_nested_paths(self):
        """Кеш работает для вложенных путей."""
        ctx = Context(user=UserInfo(user_id="42", extra={"org": "acme"}))

        # Заполняем кеш
        ctx.resolve("user.user_id")
        ctx.resolve("user.extra.org")

        # Проверяем кеш
        assert "user.user_id" in ctx._resolve_cache
        assert "user.extra.org" in ctx._resolve_cache
        assert ctx._resolve_cache["user.user_id"] == "42"
        assert ctx._resolve_cache["user.extra.org"] == "acme"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Ленивая инициализация кеша
    # ------------------------------------------------------------------

    def test_cache_lazy_initialization(self):
        """Кеш создается только при первом вызове resolve."""
        user = UserInfo(user_id="42")

        # До первого resolve кеша нет
        assert not hasattr(user, "_resolve_cache")

        # Первый вызов создает кеш
        user.resolve("user_id")
        assert hasattr(user, "_resolve_cache")
        assert isinstance(user._resolve_cache, dict)

    def test_cache_persists_across_calls(self):
        """Кеш сохраняется между разными вызовами resolve."""
        user = UserInfo(user_id="42", extra={"org": "acme"})

        # Первый вызов создает кеш
        user.resolve("user_id")
        cache_id = id(user._resolve_cache)

        # Второй вызов использует тот же кеш
        user.resolve("extra.org")
        assert id(user._resolve_cache) == cache_id
