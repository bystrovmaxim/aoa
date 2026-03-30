# src/action_machine/core/readable_mixin.py
"""
Миксин для реализации протокола ReadableDataProtocol на основе атрибутов объекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ReadableMixin обеспечивает dict-подобный доступ к полям любого объекта:
dataclass, pydantic BaseModel, обычного класса. Используется в BaseParams,
BaseResult, BaseState, Context, UserInfo, RequestInfo, RuntimeInfo.

Обеспечивает два уровня доступа к данным:
    1. Плоский доступ — через __getitem__, get, keys, values, items.
    2. Dot-path доступ — через метод resolve, который обходит вложенные
       объекты по цепочке ключей, разделённых точкой.

═══════════════════════════════════════════════════════════════════════════════
СОВМЕСТИМОСТЬ С PYDANTIC BASEMODEL
═══════════════════════════════════════════════════════════════════════════════

Pydantic BaseModel хранит данные полей в атрибутах экземпляра. ReadableMixin
определяет тип объекта через isinstance(self, BaseModel) и выбирает
стратегию получения списка полей:

- Для pydantic BaseModel: список полей берётся из type(self).model_fields.
  Обращение через класс (type(self)), а не через экземпляр, чтобы избежать
  DeprecationWarning в Pydantic V2.11+. Это гарантирует, что возвращаются
  только объявленные поля модели, без внутренних атрибутов pydantic.

- Для dataclass и обычных классов: список полей берётся из vars(self)
  с фильтрацией приватных атрибутов (начинающихся с '_').

Значения полей во всех случаях читаются через getattr(self, key),
что работает единообразно для pydantic, dataclass и обычных классов.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА RESOLVE
═══════════════════════════════════════════════════════════════════════════════

Три стратегии навигации по вложенным объектам:
    - _resolve_step_readable  → обход через __getitem__ (ReadableMixin).
    - _resolve_step_dict      → обход через dict-доступ.
    - _resolve_step_generic   → обход через getattr (произвольные объекты).

Метод _resolve_one_step выбирает стратегию по типу текущего объекта.
Метод resolve вызывает _resolve_one_step в цикле по сегментам dot-path.

Результаты resolve кешируются лениво в словаре _resolve_cache. Кеш
создаётся при первом вызове resolve через object.__setattr__, что
совместимо с frozen pydantic-моделями (BaseParams с frozen=True).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    >>> from pydantic import Field
    >>> from action_machine.core.base_params import BaseParams
    >>> class OrderParams(BaseParams):
    ...     user_id: str = Field(description="ID пользователя")
    ...     amount: float = Field(description="Сумма", gt=0)
    >>> params = OrderParams(user_id="agent_1", amount=1500.0)
    >>> params["user_id"]
    'agent_1'
    >>> params.resolve("amount")
    1500.0
    >>> params.keys()
    ['user_id', 'amount']
    >>> params.values()
    ['agent_1', 1500.0]
    >>> params.items()
    [('user_id', 'agent_1'), ('amount', 1500.0)]
"""

from pydantic import BaseModel

# Сентинел для отличия «атрибут не найден» от «атрибут равен None».
_SENTINEL: object = object()


class ReadableMixin:
    """
    Реализует ReadableDataProtocol через атрибуты объекта.

    Позволяет обращаться к полям как через точку (obj.field),
    так и через dict-подобный доступ (obj["field"]).

    Метод resolve обеспечивает навигацию по вложенным объектам
    через dot-path строки вида "user.roles" или "request.trace_id".

    Совместим с pydantic BaseModel (включая frozen=True), dataclass
    и обычными классами.

    Результаты resolve кешируются в _resolve_cache.
    """

    _resolve_cache: dict[str, object]

    def _get_field_names(self) -> list[str]:
        """
        Возвращает список имён публичных полей объекта.

        Для pydantic BaseModel использует type(self).model_fields —
        обращение через класс, а не через экземпляр, чтобы избежать
        DeprecationWarning в Pydantic V2.11+. Гарантированно возвращает
        только объявленные поля модели, исключая внутренние атрибуты pydantic.

        Для dataclass и обычных классов использует vars(self) с фильтрацией
        приватных атрибутов (начинающихся с '_').

        Возвращает:
            list[str] — имена публичных полей.
        """
        if isinstance(self, BaseModel):
            return list(type(self).model_fields.keys())
        return [k for k in vars(self) if not k.startswith("_")]

    def __getitem__(self, key: str) -> object:
        """
        Возвращает значение атрибута по имени ключа.

        Работает единообразно для pydantic, dataclass и обычных классов
        через getattr.

        Аргументы:
            key: имя атрибута (строка).

        Возвращает:
            Значение атрибута.

        Исключения:
            KeyError: если атрибут не существует.
        """
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def __contains__(self, key: str) -> bool:
        """
        Проверяет наличие атрибута по имени.

        Аргументы:
            key: имя атрибута.

        Возвращает:
            True если атрибут существует.
        """
        return hasattr(self, key)

    def get(self, key: str, default: object = None) -> object:
        """
        Безопасное получение значения атрибута с дефолтом.

        Аргументы:
            key: имя атрибута.
            default: значение, возвращаемое при отсутствии атрибута.

        Возвращает:
            Значение атрибута или default.
        """
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """
        Возвращает список имён всех публичных полей объекта.

        Для pydantic BaseModel возвращает имена полей модели (model_fields).
        Для остальных классов возвращает публичные атрибуты из vars(self).

        Возвращает:
            list[str] — список имён полей.
        """
        return self._get_field_names()

    def values(self) -> list[object]:
        """
        Возвращает список значений всех публичных полей объекта.

        Порядок соответствует порядку keys().

        Возвращает:
            list[object] — список значений.
        """
        return [getattr(self, k) for k in self._get_field_names()]

    def items(self) -> list[tuple[str, object]]:
        """
        Возвращает список пар (ключ, значение) для всех публичных полей.

        Порядок соответствует порядку keys().

        Возвращает:
            list[tuple[str, object]] — список пар.
        """
        return [(k, getattr(self, k)) for k in self._get_field_names()]

    # ─────────────────────────────────────────────────────────────────────
    # Стратегии навигации для resolve
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_step_readable(
        current: "ReadableMixin",
        segment: str,
    ) -> object:
        """
        Шаг навигации для объектов с ReadableMixin.

        Использует __getitem__ для доступа к полю по имени.
        Если ключ не найден (KeyError), возвращает _SENTINEL.

        Аргументы:
            current: текущий объект (ReadableMixin).
            segment: имя поля для перехода.

        Возвращает:
            Значение поля или _SENTINEL если не найдено.
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

        Аргументы:
            current: текущий словарь.
            segment: ключ для поиска.

        Возвращает:
            Значение по ключу или _SENTINEL если не найдено.
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

        Аргументы:
            current: произвольный объект.
            segment: имя атрибута.

        Возвращает:
            Значение атрибута или _SENTINEL если не найдено.
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

        Аргументы:
            current: текущий объект на этом шаге навигации.
            segment: имя ключа/атрибута для перехода.

        Возвращает:
            Найденное значение или _SENTINEL если шаг не удался.
        """
        if isinstance(current, ReadableMixin):
            return self._resolve_step_readable(current, segment)
        if isinstance(current, dict):
            return self._resolve_step_dict(current, segment)
        return self._resolve_step_generic(current, segment)

    # ─────────────────────────────────────────────────────────────────────
    # Основной метод resolve
    # ─────────────────────────────────────────────────────────────────────

    def resolve(self, dotpath: str, default: object = None) -> object:
        """
        Разрешает dot-path строку, обходя вложенные объекты по цепочке.

        Поддерживает три типа промежуточных объектов на каждом шаге:
            1. Объект с ReadableMixin — используется __getitem__.
            2. dict — используется dict[segment].
            3. Любой другой объект — используется getattr.

        Если на любом шаге цепочки значение не найдено, метод возвращает
        default без выброса исключения.

        Результаты кешируются в _resolve_cache. Кеш создаётся лениво
        через object.__setattr__, что совместимо с frozen pydantic-моделями.

        Аргументы:
            dotpath: строка вида "user.user_id" или "request.tags.ab_variant".
            default: значение, возвращаемое если путь не удалось разрешить.

        Возвращает:
            Найденное значение или default.
        """
        # Ленивая инициализация кеша.
        # object.__setattr__ используется вместо self._resolve_cache = {}
        # для совместимости с frozen pydantic-моделями (BaseParams).
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
