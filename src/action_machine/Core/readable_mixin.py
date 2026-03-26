# src/action_machine/core/readable_mixin.py
"""
Миксин для реализации протокола ReadableDataProtocol на основе атрибутов объекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Предназначен для использования в dataclass-классах, наследующих BaseParams
и BaseResult, в BaseState (состояние конвейера аспектов), а также в
Context-компонентах (UserInfo, RequestInfo, RuntimeInfo).

Обеспечивает два уровня доступа к данным:
    1. Плоский доступ — через __getitem__, get, keys и т.д.
    2. Dot-path доступ — через метод resolve, который обходит вложенные объекты
       по цепочке ключей, разделённых точкой.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА RESOLVE
═══════════════════════════════════════════════════════════════════════════════

Три стратегии навигации по вложенным объектам реализованы как отдельные
статические методы:
    - _resolve_step_readable  → обход через __getitem__
    - _resolve_step_dict      → обход через dict-доступ
    - _resolve_step_generic   → обход через getattr

Единый метод _resolve_one_step выбирает стратегию по типу текущего объекта.
Основной метод resolve вызывает _resolve_one_step в цикле и управляет кешем.

Результаты resolve кешируются лениво в словаре _resolve_cache. Кеш
инициализируется через object.__setattr__ для совместимости с frozen dataclass.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    >>> from action_machine.context.context import Context
    >>> from action_machine.context.user_info import UserInfo
    >>> user = UserInfo(user_id="agent_1", roles=["admin"])
    >>> ctx = Context(user=user)
    >>> ctx.resolve("user.user_id")
    'agent_1'
    >>> ctx.resolve("user.nonexistent", default="<none>")
    '<none>'
"""

# Сентинел для отличия «атрибут не найден» от «атрибут равен None».
_SENTINEL: object = object()


class ReadableMixin:
    """
    Реализует ReadableDataProtocol через атрибуты объекта.

    Позволяет обращаться к полям dataclass как через точку (obj.field),
    так и через dict-подобный доступ (obj["field"]).

    Метод resolve обеспечивает навигацию по вложенным объектам
    через dot-path строки вида "user.roles" или "request.trace_id".

    Результаты кешируются в _resolve_cache для повторных вызовов.
    """

    _resolve_cache: dict[str, object]

    def __getitem__(self, key: str) -> object:
        """
        Возвращает значение атрибута по имени ключа.

        Исключения:
            KeyError: если атрибут не существует.
        """
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def __contains__(self, key: str) -> bool:
        """Проверяет наличие атрибута по имени."""
        return hasattr(self, key)

    def get(self, key: str, default: object = None) -> object:
        """Безопасное получение значения атрибута с дефолтом."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """
        Возвращает список имён всех публичных полей объекта.

        Публичными считаются все атрибуты, имя которых
        не начинается с символа подчёркивания '_'.
        """
        return [k for k, _ in vars(self).items() if not k.startswith("_")]

    def values(self) -> list[object]:
        """Возвращает список значений всех публичных полей объекта."""
        return [v for k, v in vars(self).items() if not k.startswith("_")]

    def items(self) -> list[tuple[str, object]]:
        """Возвращает список пар (ключ, значение) для всех публичных полей."""
        return [(k, v) for k, v in vars(self).items() if not k.startswith("_")]

    # ---------- Стратегии навигации для resolve ----------

    @staticmethod
    def _resolve_step_readable(
        current: "ReadableMixin",
        segment: str,
    ) -> object:
        """
        Шаг навигации для объектов с ReadableMixin.

        Использует __getitem__ для доступа к полю по имени.
        Если ключ не найден (KeyError), возвращает _SENTINEL.
        """
        try:
            return current[segment]
        except KeyError:
            return _SENTINEL

    @staticmethod
    def _resolve_step_dict(
        current: dict[str, object],
        segment: str,
    ) -> object:
        """
        Шаг навигации для обычных словарей.

        Проверяет наличие ключа через оператор in.
        Если ключ есть — возвращает значение, иначе _SENTINEL.
        """
        if segment in current:
            return current[segment]
        return _SENTINEL

    @staticmethod
    def _resolve_step_generic(
        current: object,
        segment: str,
    ) -> object:
        """
        Шаг навигации для произвольных объектов через getattr.

        Используется как fallback для объектов, которые не являются
        ни ReadableMixin, ни dict.
        """
        return getattr(current, segment, _SENTINEL)

    def _resolve_one_step(
        self,
        current: object,
        segment: str,
    ) -> object:
        """
        Выполняет один шаг навигации, выбирая стратегию по типу текущего объекта.

        Порядок проверки isinstance определяет приоритет стратегий:
            1. ReadableMixin — объекты с dict-подобным доступом через __getitem__.
            2. dict — обычные словари (extra, вложенные структуры).
            3. Любой другой объект — fallback через getattr.
        """
        if isinstance(current, ReadableMixin):
            return self._resolve_step_readable(current, segment)
        if isinstance(current, dict):
            return self._resolve_step_dict(current, segment)
        return self._resolve_step_generic(current, segment)

    # ---------- Основной метод resolve ----------

    def resolve(self, dotpath: str, default: object = None) -> object:
        """
        Разрешает dot-path строку, обходя вложенные объекты по цепочке.

        Поддерживает три типа промежуточных объектов на каждом шаге:
            1. Объект с ReadableMixin — используется __getitem__.
            2. dict — используется dict[segment].
            3. Любой другой объект — используется getattr.

        Если на любом шаге цепочки значение не найдено, метод возвращает
        default без выброса исключения.

        Результаты кешируются в _resolve_cache.

        Аргументы:
            dotpath: строка вида "user.user_id" или "request.tags.ab_variant".
            default: значение, возвращаемое если путь не удалось разрешить.

        Возвращает:
            Найденное значение или default.
        """
        # Ленивая инициализация кеша
        try:
            cache: dict[str, object] = self.__dict__["_resolve_cache"]
        except KeyError:
            cache = {}
            object.__setattr__(self, "_resolve_cache", cache)

        # Проверяем кеш
        if dotpath in cache:
            return cache[dotpath]

        # Разбиваем путь на сегменты и обходим цепочку
        segments: list[str] = dotpath.split(".")
        current: object = self

        for segment in segments:
            current = self._resolve_one_step(current, segment)
            if current is _SENTINEL:
                cache[dotpath] = default
                return default

        cache[dotpath] = current
        return current
