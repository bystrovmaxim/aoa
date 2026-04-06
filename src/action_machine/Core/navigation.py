# src/action_machine/core/navigation.py
"""
Единый навигатор по dot-path для всех компонентов фреймворка ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит класс DotPathNavigator — единственную точку навигации
по цепочкам вложенных объектов через dot-path строки вида "user.address.city".

Все компоненты фреймворка, которым нужна навигация по вложенным структурам,
делегируют её DotPathNavigator:

    - BaseSchema.resolve() — для пользовательского доступа к данным [2].
    - VariableSubstitutor — для разрешения переменных в шаблонах логирования [4].

Это гарантирует единообразное поведение: одни и те же правила приоритета
типов, одна и та же обработка None-значений, одна и та же обработка
отсутствующих атрибутов.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРНЫЕ ОГРАНИЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

Модуль принадлежит пакету core и не имеет зависимостей от других пакетов
фреймворка (logging, context и т.д.). Это принципиальное ограничение:
ядро не должно знать о подсистемах, которые его используют.

Поддержка объектов из других пакетов (например, LogScope из logging [3])
обеспечивается через утиную типизацию: навигатор проверяет наличие
интерфейса __getitem__, а не конкретный тип класса. Любой объект,
реализующий __getitem__ с выбросом KeyError при отсутствии ключа,
автоматически поддерживается навигатором без явной зависимости.

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИЯ НАВИГАЦИИ
═══════════════════════════════════════════════════════════════════════════════

На каждом шаге навигатор определяет тип текущего объекта и выбирает
стратегию доступа к следующему сегменту пути. Приоритет стратегий:

    1. BaseSchema  → __getitem__ (dict-подобный доступ pydantic-модели) [2].
    2. dict        → прямой доступ по ключу.
    3. Объект с __getitem__ → try/except KeyError.
       Сюда попадают LogScope [3] и любые другие объекты с dict-подобным
       интерфейсом, не являющиеся dict или BaseSchema.
    4. Любой объект → getattr.

Порядок важен:
- BaseSchema проверяется раньше dict, потому что BaseSchema не является
  dict, но имеет собственный __getitem__ с поддержкой extra-полей [2].
- dict проверяется раньше общего __getitem__, потому что прямой доступ
  по ключу эффективнее try/except.
- Общий __getitem__ (ветка 3) — fallback для всех объектов с dict-подобным
  интерфейсом, которые не попали в предыдущие ветки.

═══════════════════════════════════════════════════════════════════════════════
SENTINEL
═══════════════════════════════════════════════════════════════════════════════

Модуль определяет _SENTINEL — уникальный объект-маркер, означающий
«значение не найдено». Он используется вместо None, потому что None —
валидное значение поля [6] [7]. Сравнение выполняется только через
оператор `is`.

_SENTINEL используется:
    - Внутри DotPathNavigator для возврата из шагов навигации.
    - В BaseSchema.resolve() для проверки результата навигации [2].
    - В VariableSubstitutor для проверки результата навигации [4].

═══════════════════════════════════════════════════════════════════════════════
ДВА РЕЖИМА НАВИГАЦИИ
═══════════════════════════════════════════════════════════════════════════════

navigate(root, dotpath)
    Простая навигация. Возвращает финальное значение или _SENTINEL.
    Используется в BaseSchema.resolve(), где нужен только результат [2].

navigate_with_source(root, dotpath)
    Навигация с отслеживанием источника. Возвращает кортеж
    (value, source, last_segment), где source — предпоследний объект
    в цепочке, а last_segment — имя последнего сегмента пути.
    Используется в VariableSubstitutor для обнаружения @sensitive-свойств:
    маскирование проверяется на source по имени last_segment [4].

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.core.navigation import DotPathNavigator, _SENTINEL

    # Простая навигация
    result = DotPathNavigator.navigate(schema, "user.address.city")
    if result is _SENTINEL:
        result = default_value

    # Навигация с отслеживанием источника (для маскирования)
    value, source, segment = DotPathNavigator.navigate_with_source(
        schema, "user.secret_token"
    )
    if value is not _SENTINEL and source is not None:
        config = get_sensitive_config(source, segment)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.core.base_schema import BaseSchema

# Уникальный объект-маркер, означающий «значение не найдено».
# Используется вместо None, потому что None — валидное значение поля.
# Сравнение выполняется только через оператор `is`, коллизии невозможны.
_SENTINEL: object = object()

# Кеш для ленивого импорта BaseSchema. Заполняется при первом вызове
# resolve_step(). Это избавляет от поиска в sys.modules на каждом шаге
# навигации, сохраняя при этом отсутствие циклической зависимости
# на уровне модуля.
_BaseSchemaType: type | None = None


class DotPathNavigator:
    """
    Единая точка навигации по dot-path строкам для всех компонентов фреймворка.

    Все методы — статические. Класс не хранит состояния и не требует
    создания экземпляра. Группировка в класс — для пространства имён
    и единой точки импорта.

    Стратегия приоритетов на каждом шаге:
        1. BaseSchema        → __getitem__ [2].
        2. dict              → прямой доступ по ключу.
        3. Объект с __getitem__ → try/except KeyError [3].
        4. Любой объект      → getattr.
    """

    # ─── шаги навигации по типу объекта ───────────────────────────────

    @staticmethod
    def _step_schema(current: BaseSchema, segment: str) -> object:
        """
        Шаг навигации для объектов BaseSchema.

        Использует __getitem__, который работает через getattr и
        поддерживает как объявленные поля (model_fields), так и
        динамические extra-поля (для наследников с extra="allow") [2].

        Аргументы:
            current: текущий объект BaseSchema.
            segment: имя поля для доступа.

        Возвращает:
            Значение поля или _SENTINEL если поле не найдено.
        """
        try:
            return current[segment]
        except (KeyError, TypeError):
            return _SENTINEL

    @staticmethod
    def _step_dict(current: dict, segment: str) -> object:
        """
        Шаг навигации для обычных словарей.

        Использует прямую проверку наличия ключа, что эффективнее
        try/except для словарей.

        Аргументы:
            current: текущий словарь.
            segment: ключ для доступа.

        Возвращает:
            Значение по ключу или _SENTINEL если ключ отсутствует.
        """
        if segment in current:
            return current[segment]
        return _SENTINEL

    @staticmethod
    def _step_getitem(current: object, segment: str) -> object:
        """
        Шаг навигации для объектов с __getitem__, не являющихся
        dict или BaseSchema.

        Сюда попадают LogScope [3] и любые другие объекты, реализующие
        dict-подобный интерфейс (__getitem__ с выбросом KeyError при
        отсутствии ключа). Навигатор не зависит от конкретных типов
        этих объектов — достаточно наличия интерфейса.

        Аргументы:
            current: текущий объект с __getitem__.
            segment: ключ для доступа.

        Возвращает:
            Значение по ключу или _SENTINEL если ключ не найден.
        """
        try:
            return current[segment]  # type: ignore[index]
        except (KeyError, TypeError, IndexError):
            return _SENTINEL

    @staticmethod
    def _step_generic(current: object, segment: str) -> object:
        """
        Шаг навигации для произвольных объектов через getattr.

        Используется как финальный fallback для объектов, не являющихся
        BaseSchema, dict и не имеющих __getitem__.

        Аргументы:
            current: текущий объект.
            segment: имя атрибута для доступа.

        Возвращает:
            Значение атрибута или _SENTINEL если атрибут не найден.
        """
        return getattr(current, segment, _SENTINEL)

    # ─── диспетчер одного шага ────────────────────────────────────────

    @staticmethod
    def resolve_step(current: object, segment: str) -> object:
        """
        Выполняет один шаг навигации, выбирая стратегию по типу объекта.

        Порядок проверок определяет приоритет:
            1. BaseSchema — pydantic-модель с dict-подобным доступом [2].
            2. dict — обычный словарь Python.
            3. Объект с __getitem__ — любой объект с dict-подобным
            интерфейсом (LogScope [3] и др.).
            4. Любой другой объект — доступ через getattr.

        Импорт BaseSchema выполняется один раз при первом вызове и
        кешируется в переменной модуля _BaseSchemaType. Это избавляет
        от поиска в sys.modules на каждом шаге навигации, сохраняя
        при этом отсутствие циклической зависимости на уровне модуля.

        Аргументы:
            current: текущий объект в цепочке навигации.
            segment: имя следующего сегмента пути.

        Возвращает:
            Значение сегмента или _SENTINEL если сегмент не найден.
        """
        global _BaseSchemaType
        if _BaseSchemaType is None:
            from action_machine.core.base_schema import BaseSchema
            _BaseSchemaType = BaseSchema

        if isinstance(current, _BaseSchemaType):
            return DotPathNavigator._step_schema(current, segment)
        if isinstance(current, dict):
            return DotPathNavigator._step_dict(current, segment)
        if hasattr(current, "__getitem__"):
            return DotPathNavigator._step_getitem(current, segment)
        return DotPathNavigator._step_generic(current, segment)

    # ─── полная навигация ─────────────────────────────────────────────

    @staticmethod
    def navigate(root: object, dotpath: str) -> object:
        """
        Полная навигация по dot-path от корневого объекта.

        Разбивает dotpath на сегменты по точкам и последовательно
        применяет resolve_step к каждому. Если на любом шаге
        результат — _SENTINEL, навигация прекращается.

        Используется в BaseSchema.resolve() для пользовательского
        доступа к вложенным данным [2].

        Аргументы:
            root: корневой объект, от которого начинается навигация.
            dotpath: строка вида "user.address.city".

        Возвращает:
            Найденное значение или _SENTINEL если путь не разрешился.

        Примеры:
            DotPathNavigator.navigate(context, "user.user_id")
            DotPathNavigator.navigate(state, "payment.txn_id")
            DotPathNavigator.navigate({"a": {"b": 1}}, "a.b")
        """
        current = root
        for segment in dotpath.split("."):
            current = DotPathNavigator.resolve_step(current, segment)
            if current is _SENTINEL:
                return _SENTINEL
        return current

    @staticmethod
    def navigate_with_source(
        root: object,
        dotpath: str,
    ) -> tuple[object, object | None, str | None]:
        """
        Навигация по dot-path с отслеживанием объекта-источника.

        Работает аналогично navigate(), но дополнительно запоминает
        предпоследний объект в цепочке (source) и имя последнего
        сегмента пути (last_segment).

        Используется в VariableSubstitutor для обнаружения
        @sensitive-свойств: декоратор @sensitive вешается на property
        объекта source, и для его обнаружения нужно знать, на каком
        объекте и по какому имени было прочитано финальное значение [4].

        Аргументы:
            root: корневой объект навигации.
            dotpath: строка вида "user.secret_token".

        Возвращает:
            Кортеж (value, source, last_segment):
                value        — найденное значение или _SENTINEL.
                source       — предпоследний объект в цепочке (или None
                               если путь пустой).
                last_segment — имя последнего сегмента пути (или None
                               если dotpath пустой).

        Примеры:
            # value="Alice", source=UserInfo(...), last_segment="name"
            DotPathNavigator.navigate_with_source(ctx, "user.name")

            # value=_SENTINEL, source=UserInfo(...), last_segment="missing"
            DotPathNavigator.navigate_with_source(ctx, "user.missing")
        """
        if not dotpath:
            return root, None, None

        segments = dotpath.split(".")
        current = root
        source: object | None = None

        for segment in segments:
            source = current
            current = DotPathNavigator.resolve_step(current, segment)
            if current is _SENTINEL:
                return _SENTINEL, source, segment

        return current, source, segments[-1]
