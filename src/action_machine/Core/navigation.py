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

    - BaseSchema.resolve() — для пользовательского доступа к данным.
    - VariableSubstitutor — для разрешения переменных в шаблонах логирования.

Это устраняет дублирование логики навигации и гарантирует единообразное
поведение: одни и те же правила приоритета типов, одна и та же обработка
None-значений, одна и та же обработка отсутствующих атрибутов.

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИЯ НАВИГАЦИИ
═══════════════════════════════════════════════════════════════════════════════

На каждом шаге навигатор определяет тип текущего объекта и выбирает
стратегию доступа к следующему сегменту пути. Приоритет стратегий:

    1. BaseSchema  → __getitem__ (dict-подобный доступ pydantic-модели).
    2. LogScope    → __getitem__ (dict-подобный доступ scope логирования).
    3. dict        → прямой доступ по ключу.
    4. Любой объект → getattr.

BaseSchema и LogScope проверяются раньше dict, потому что оба предоставляют
__getitem__ с семантикой, отличной от обычного словаря (BaseSchema работает
через getattr и поддерживает extra-поля, LogScope хранит динамические
атрибуты с сохранением порядка).

═══════════════════════════════════════════════════════════════════════════════
SENTINEL
═══════════════════════════════════════════════════════════════════════════════

Модуль определяет _SENTINEL — уникальный объект-маркер, означающий
«значение не найдено». Он используется вместо None, потому что None —
валидное значение поля. Сравнение выполняется только через оператор `is`.

_SENTINEL используется:
    - Внутри DotPathNavigator для возврата из шагов навигации.
    - В BaseSchema.resolve() для проверки результата навигации.
    - В VariableSubstitutor для проверки результата навигации.

═══════════════════════════════════════════════════════════════════════════════
ДВА РЕЖИМА НАВИГАЦИИ
═══════════════════════════════════════════════════════════════════════════════

navigate(root, dotpath)
    Простая навигация. Возвращает финальное значение или _SENTINEL.
    Используется в BaseSchema.resolve(), где нужен только результат.

navigate_with_source(root, dotpath)
    Навигация с отслеживанием источника. Возвращает кортеж
    (value, source, last_segment), где source — предпоследний объект
    в цепочке, а last_segment — имя последнего сегмента пути.
    Используется в VariableSubstitutor для обнаружения @sensitive-свойств:
    маскирование проверяется на source по имени last_segment.

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

═══════════════════════════════════════════════════════════════════════════════
ЗАВИСИМОСТИ
═══════════════════════════════════════════════════════════════════════════════

Модуль использует TYPE_CHECKING-импорты для BaseSchema и LogScope,
чтобы избежать циклических зависимостей (BaseSchema импортирует navigation,
navigation не должен импортировать BaseSchema на уровне модуля).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.core.base_schema import BaseSchema
    from action_machine.logging.log_scope import LogScope

# Уникальный объект-маркер, означающий «значение не найдено».
# Используется вместо None, потому что None — валидное значение поля.
# Сравнение выполняется только через оператор `is`, коллизии невозможны.
_SENTINEL: object = object()


class DotPathNavigator:
    """
    Единая точка навигации по dot-path строкам для всех компонентов фреймворка.

    Все методы — статические. Класс не хранит состояния и не требует
    создания экземпляра. Группировка в класс — для пространства имён
    и единой точки импорта.

    Стратегия приоритетов на каждом шаге:
        1. BaseSchema → __getitem__.
        2. LogScope   → __getitem__.
        3. dict       → прямой доступ по ключу.
        4. Любой объект → getattr.
    """

    # ─── шаги навигации по типу объекта ───────────────────────────────

    @staticmethod
    def _step_schema(current: BaseSchema, segment: str) -> object:
        """
        Шаг навигации для объектов BaseSchema.

        Использует __getitem__, который работает через getattr и
        поддерживает как объявленные поля (model_fields), так и
        динамические extra-поля (для наследников с extra="allow").

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
    def _step_scope(current: LogScope, segment: str) -> object:
        """
        Шаг навигации для объектов LogScope.

        LogScope — лёгкий объект с динамическими атрибутами и
        dict-подобным доступом через __getitem__. Не является
        pydantic-моделью, поэтому обрабатывается отдельной веткой.

        Аргументы:
            current: текущий объект LogScope.
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
    def _step_generic(current: object, segment: str) -> object:
        """
        Шаг навигации для произвольных объектов через getattr.

        Используется как fallback для объектов, не являющихся
        BaseSchema, LogScope или dict.

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
            1. BaseSchema — pydantic-модель с dict-подобным доступом.
            2. LogScope — лёгкий scope логирования с dict-подобным доступом.
            3. dict — обычный словарь Python.
            4. Любой другой объект — доступ через getattr.

        Импорты BaseSchema и LogScope выполняются внутри метода,
        чтобы избежать циклических зависимостей на уровне модуля.

        Аргументы:
            current: текущий объект в цепочке навигации.
            segment: имя следующего сегмента пути.

        Возвращает:
            Значение сегмента или _SENTINEL если сегмент не найден.
        """
        from action_machine.core.base_schema import BaseSchema
        from action_machine.logging.log_scope import LogScope

        if isinstance(current, BaseSchema):
            return DotPathNavigator._step_schema(current, segment)
        if isinstance(current, LogScope):
            return DotPathNavigator._step_scope(current, segment)
        if isinstance(current, dict):
            return DotPathNavigator._step_dict(current, segment)
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
        доступа к вложенным данным.

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
        объекте и по какому имени было прочитано финальное значение.

        Аргументы:
            root: корневой объект навигации.
            dotpath: строка вида "user.secret_token".

        Возвращает:
            Кортеж (value, source, last_segment):
                value        — найденное значение или _SENTINEL.
                source       — предпоследний объект в цепочке (или None
                               если путь пустой или состоит из одного сегмента
                               и навигация не удалась на первом шаге).
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
