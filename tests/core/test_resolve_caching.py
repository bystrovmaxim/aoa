# tests/core/test_resolve_caching.py
"""
Тесты кеширования результатов ReadableMixin.resolve().

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

resolve() кеширует результаты в словаре _resolve_cache, привязанном
к экземпляру объекта. Кеш создаётся лениво при первом вызове resolve()
через object.__setattr__(self, "_resolve_cache", {}). Использование
object.__setattr__ вместо self._resolve_cache = {} обеспечивает
совместимость с frozen pydantic-моделями (BaseParams с frozen=True).

Ключ кеша — полный dotpath (например, "user.extra.org"). Значение —
результат разрешения (включая default для отсутствующих путей).

Кеш НЕ инвалидируется при изменении объекта. Если значение атрибута
изменилось после первого resolve(), повторный resolve() вернёт
закешированное старое значение. Это осознанное решение: в рамках
одного запроса (run()) объекты params и context не меняются,
а state пересоздаётся при каждом мерже.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Ленивая инициализация:
    - До первого resolve() кеша нет (_resolve_cache не существует).
    - Первый resolve() создаёт _resolve_cache через object.__setattr__.
    - Тип кеша — dict.

Кеширование успешных результатов:
    - Повторный resolve() возвращает закешированное значение.
    - Кеш хранит тот же объект (is-проверка для мутабельных значений).
    - Изменение оригинала после кеширования не влияет на кеш.

Кеширование default для отсутствующих путей:
    - resolve("missing") → None закешировано.
    - resolve("missing", default="X") → "X" закешировано.
    - Повторный resolve("missing", default="Y") вернёт первый default.

Независимость кеша:
    - Разные dotpath — разные записи в кеше.
    - Кеш одного экземпляра не влияет на другой экземпляр того же класса.

Кеш на frozen pydantic-модели:
    - resolve() работает на BaseParams (frozen=True) благодаря
      object.__setattr__.
"""

from pydantic import Field

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams

# ═════════════════════════════════════════════════════════════════════════════
# Ленивая инициализация кеша
# ═════════════════════════════════════════════════════════════════════════════


class TestLazyInit:
    """Кеш _resolve_cache создаётся лениво при первом вызове resolve()."""

    def test_no_cache_before_first_resolve(self) -> None:
        """
        До первого вызова resolve() атрибут _resolve_cache не существует.

        Объект UserInfo создаётся через @dataclass. _resolve_cache
        не входит в поля dataclass и не создаётся в __init__.
        Он появится только при первом resolve() через
        object.__setattr__(self, "_resolve_cache", {}).
        """
        # Arrange — свежий UserInfo, resolve() ещё не вызывался
        user = UserInfo(user_id="42")

        # Act — проверяем наличие _resolve_cache в __dict__
        has_cache = "_resolve_cache" in user.__dict__

        # Assert — кеша ещё нет
        assert has_cache is False

    def test_first_resolve_creates_cache(self) -> None:
        """
        Первый вызов resolve() создаёт _resolve_cache как пустой dict,
        затем записывает в него результат.

        Внутри resolve(): try/except KeyError на self.__dict__["_resolve_cache"]
        → KeyError → object.__setattr__(self, "_resolve_cache", {}).
        """
        # Arrange — свежий UserInfo
        user = UserInfo(user_id="42")

        # Act — первый resolve создаёт кеш
        user.resolve("user_id")

        # Assert — кеш существует и является dict
        assert "_resolve_cache" in user.__dict__
        assert isinstance(user._resolve_cache, dict)

    def test_cache_contains_resolved_path(self) -> None:
        """
        После resolve("user_id") кеш содержит запись "user_id" → "42".

        Ключ кеша — полный dotpath, значение — результат разрешения.
        """
        # Arrange — свежий UserInfo
        user = UserInfo(user_id="42")

        # Act — resolve заполняет кеш
        user.resolve("user_id")

        # Assert — кеш содержит ключ "user_id" со значением "42"
        assert "user_id" in user._resolve_cache
        assert user._resolve_cache["user_id"] == "42"

    def test_cache_persists_across_calls(self) -> None:
        """
        Кеш сохраняется между разными вызовами resolve().

        Первый resolve("user_id") создаёт кеш. Второй resolve("extra.org")
        добавляет запись в тот же dict. Объект кеша (id) не меняется.
        """
        # Arrange — UserInfo с двумя полями для resolve
        user = UserInfo(user_id="42", extra={"org": "acme"})

        # Act — первый resolve создаёт кеш
        user.resolve("user_id")
        cache_id_after_first = id(user._resolve_cache)

        # Act — второй resolve добавляет запись в тот же кеш
        user.resolve("extra.org")
        cache_id_after_second = id(user._resolve_cache)

        # Assert — тот же объект кеша (dict), не пересоздан
        assert cache_id_after_first == cache_id_after_second

        # Assert — обе записи в кеше
        assert "user_id" in user._resolve_cache
        assert "extra.org" in user._resolve_cache


# ═════════════════════════════════════════════════════════════════════════════
# Кеширование успешных результатов
# ═════════════════════════════════════════════════════════════════════════════


class TestCacheHit:
    """Повторный resolve() возвращает закешированное значение."""

    def test_second_call_returns_cached_value(self) -> None:
        """
        Повторный resolve("user_id") возвращает то же значение из кеша,
        не обращаясь к атрибутам объекта повторно.

        На практике это оптимизация: шаблон логирования может содержать
        несколько обращений к одному пути ({%context.user.user_id}
        в нескольких местах), и кеш избавляет от повторного обхода цепочки.
        """
        # Arrange — UserInfo с user_id
        user = UserInfo(user_id="42")

        # Act — два вызова resolve с одним путём
        first = user.resolve("user_id")
        second = user.resolve("user_id")

        # Assert — одинаковые значения
        assert first == "42"
        assert second == "42"

    def test_cached_mutable_object_is_same_reference(self) -> None:
        """
        Кеш хранит ссылку на объект, не копию. Для мутабельных значений
        (list, dict) повторный resolve() возвращает тот же объект (is-проверка).

        Это означает, что изменение возвращённого списка изменит
        и кеш. В рамках ActionMachine это не проблема: params и context
        не меняются в течение запроса.
        """
        # Arrange — UserInfo с extra-словарём, содержащим список
        user = UserInfo(extra={"data": [1, 2, 3]})

        # Act — два вызова resolve, оба возвращают тот же объект
        first = user.resolve("extra.data")
        second = user.resolve("extra.data")

        # Assert — один и тот же объект в памяти (is, а не ==)
        assert first is second
        assert id(first) == id(second)

    def test_cache_not_invalidated_on_mutation(self) -> None:
        """
        Кеш НЕ инвалидируется при изменении объекта.

        Если значение атрибута изменилось после первого resolve(),
        повторный resolve() вернёт старое закешированное значение.
        Это осознанное решение: в ActionMachine params (frozen) и
        context не меняются в течение запроса, а state пересоздаётся.
        """
        # Arrange — UserInfo с extra, затем первый resolve для заполнения кеша
        user = UserInfo(user_id="42", extra={"key": "original"})
        first = user.resolve("extra.key")

        # Act — изменяем значение в extra ПОСЛЕ кеширования
        user.extra["key"] = "changed"

        # Act — повторный resolve возвращает СТАРОЕ значение из кеша
        second = user.resolve("extra.key")

        # Assert — первый resolve вернул "original"
        assert first == "original"

        # Assert — второй resolve вернул тоже "original" (из кеша),
        # а не "changed" (из изменённого extra)
        assert second == "original"


# ═════════════════════════════════════════════════════════════════════════════
# Кеширование default для отсутствующих путей
# ═════════════════════════════════════════════════════════════════════════════


class TestCacheDefault:
    """Кеширование default-значений для несуществующих путей."""

    def test_none_default_cached(self) -> None:
        """
        resolve("missing") без default → None записывается в кеш.

        При отсутствии пути _resolve_one_step возвращает _SENTINEL,
        цикл прерывается, default (None) записывается в _resolve_cache
        и возвращается.
        """
        # Arrange — UserInfo без атрибута "missing"
        user = UserInfo(user_id="42")

        # Act — первый resolve для заполнения кеша
        result = user.resolve("missing")

        # Assert — None записан в кеш
        assert result is None
        assert user._resolve_cache["missing"] is None

    def test_explicit_default_cached(self) -> None:
        """
        resolve("missing", default="fallback") → "fallback" записывается в кеш.
        """
        # Arrange — UserInfo без атрибута "missing"
        user = UserInfo(user_id="42")

        # Act — resolve с явным default
        result = user.resolve("missing", default="fallback")

        # Assert — "fallback" записан в кеш
        assert result == "fallback"
        assert user._resolve_cache["missing"] == "fallback"

    def test_cached_default_wins_over_new_default(self) -> None:
        """
        Повторный resolve("missing", default="other") возвращает
        ПЕРВЫЙ закешированный default, а не новый.

        Кеш привязан к dotpath. Первый вызов записал default в кеш.
        Второй вызов находит запись в кеше и возвращает её, не выполняя
        повторного обхода цепочки.
        """
        # Arrange — UserInfo без "missing", первый resolve с default="first"
        user = UserInfo(user_id="42")
        user.resolve("missing", default="first")

        # Act — повторный resolve с ДРУГИМ default
        result = user.resolve("missing", default="second")

        # Assert — возвращён ПЕРВЫЙ default "first" из кеша,
        # а не "second" из второго вызова
        assert result == "first"

    def test_cached_none_wins_over_explicit_default(self) -> None:
        """
        Если первый resolve("missing") записал None в кеш,
        повторный resolve("missing", default="X") вернёт None из кеша.

        Это может быть неожиданным, но это корректное поведение кеша:
        кеш не различает "результат None" и "default None".
        """
        # Arrange — первый resolve без default → None в кеше
        user = UserInfo(user_id="42")
        user.resolve("missing")

        # Act — повторный resolve с явным default
        result = user.resolve("missing", default="fallback")

        # Assert — None из кеша, не "fallback"
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Независимость кеша
# ═════════════════════════════════════════════════════════════════════════════


class TestCacheIndependence:
    """Кеш привязан к экземпляру и dotpath."""

    def test_different_paths_different_cache_entries(self) -> None:
        """
        Разные dotpath — разные записи в кеше.

        Кеш — плоский dict {dotpath: value}. Каждый уникальный
        dotpath — отдельный ключ.
        """
        # Arrange — UserInfo с двумя полями
        user = UserInfo(user_id="42", extra={"org": "acme"})

        # Act — resolve двух разных путей
        user.resolve("user_id")
        user.resolve("extra.org")

        # Assert — два разных ключа в кеше
        assert "user_id" in user._resolve_cache
        assert "extra.org" in user._resolve_cache
        assert user._resolve_cache["user_id"] == "42"
        assert user._resolve_cache["extra.org"] == "acme"

    def test_nested_paths_in_context(self) -> None:
        """
        Вложенные пути через Context кешируются с полным dotpath.

        "user.user_id" и "user.extra.org" — два разных ключа в кеше
        объекта Context, не в кеше UserInfo.
        """
        # Arrange — Context с UserInfo
        ctx = Context(user=UserInfo(user_id="42", extra={"org": "acme"}))

        # Act — resolve двух вложенных путей
        ctx.resolve("user.user_id")
        ctx.resolve("user.extra.org")

        # Assert — оба пути закешированы в кеше Context
        assert "user.user_id" in ctx._resolve_cache
        assert "user.extra.org" in ctx._resolve_cache
        assert ctx._resolve_cache["user.user_id"] == "42"
        assert ctx._resolve_cache["user.extra.org"] == "acme"

    def test_different_instances_independent_caches(self) -> None:
        """
        Кеш привязан к конкретному экземпляру объекта.

        Два разных UserInfo с одинаковыми данными имеют разные кеши.
        resolve на одном не влияет на кеш другого.
        """
        # Arrange — два экземпляра с одинаковыми данными
        user1 = UserInfo(user_id="42")
        user2 = UserInfo(user_id="42")

        # Act — resolve только на первом
        user1.resolve("user_id")

        # Assert — кеш есть только у первого
        assert "_resolve_cache" in user1.__dict__
        assert "_resolve_cache" not in user2.__dict__


# ═════════════════════════════════════════════════════════════════════════════
# Кеш на frozen pydantic-модели
# ═════════════════════════════════════════════════════════════════════════════


class TestCacheOnFrozenPydantic:
    """resolve() и кеш работают на frozen pydantic-моделях (BaseParams)."""

    def test_resolve_works_on_frozen_params(self) -> None:
        """
        resolve() работает на BaseParams (frozen=True).

        Pydantic frozen-модели запрещают self.attr = value.
        resolve() обходит это через object.__setattr__(self, "_resolve_cache", {}),
        который вызывает object.__setattr__ напрямую, минуя pydantic-валидацию.
        """
        # Arrange — frozen pydantic-модель
        class TestParams(BaseParams):
            name: str = Field(description="Имя")

        params = TestParams(name="Alice")

        # Act — resolve на frozen-модели не бросает ValidationError
        result = params.resolve("name")

        # Assert — значение извлечено, кеш создан
        assert result == "Alice"
        assert "_resolve_cache" in params.__dict__
        assert params._resolve_cache["name"] == "Alice"

    def test_repeated_resolve_on_frozen_params(self) -> None:
        """
        Повторный resolve() на frozen-модели возвращает из кеша.
        """
        # Arrange — frozen pydantic-модель
        class TestParams(BaseParams):
            value: int = Field(description="Значение")

        params = TestParams(value=99)

        # Act — два вызова
        first = params.resolve("value")
        second = params.resolve("value")

        # Assert — оба возвращают одно и то же
        assert first == 99
        assert second == 99
