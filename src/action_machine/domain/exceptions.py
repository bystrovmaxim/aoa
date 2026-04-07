# src/action_machine/domain/exceptions.py
"""
Исключения подсистемы доменной модели ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит все пользовательские исключения, специфичные для доменной
модели: сущностей (BaseEntity), связей (контейнеры связей), жизненных
циклов (Lifecycle) и координатора сущностей (EntityCoordinator).

Исключения вынесены в отдельный модуль (а не в core/exceptions.py), потому
что доменная модель — независимая подсистема, не имеющая обратных
зависимостей от ядра ActionMachine. Ядро (core) не импортирует доменные
исключения. Доменный код импортирует только core-исключения (NamingSuffixError)
через стандартные пути.

═══════════════════════════════════════════════════════════════════════════════
ИСКЛЮЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

FieldNotLoadedError
    Обращение к полю сущности, которое не было загружено при частичной
    загрузке через BaseEntity.partial(). Наследует AttributeError.

RelationNotLoadedError
    Обращение к атрибуту связанной сущности через контейнер связи
    (CompositeOne, AssociationOne и т.д.), когда объект (entity) не
    загружен — загружен только id. Наследует AttributeError.

EntityDecoratorError
    Ошибки декоратора @entity. Наследует TypeError.

LifecycleValidationError
    Нарушение целостности конечного автомата Lifecycle. Выбрасывается
    координатором сущностей при сборке метаданных.
"""

from __future__ import annotations

from typing import Any


class FieldNotLoadedError(AttributeError):
    """
    Обращение к незагруженному полю частично загруженной сущности.

    Выбрасывается при доступе к атрибуту, который не был передан
    в BaseEntity.partial(). Наследует AttributeError, потому что
    семантически это ошибка доступа к атрибуту — поле существует
    в схеме класса, но не было загружено в данном экземпляре.

    Наследование от AttributeError обеспечивает корректное поведение
    с hasattr(): hasattr(entity, "status") вернёт False для
    незагруженного поля.

    Это НЕ lazy-loading. Никаких скрытых запросов к хранилищу. Поле
    либо загружено при создании через partial(), либо нет. Обращение
    к незагруженному полю — немедленная ошибка.

    Атрибуты:
        field_name : str
            Имя поля, к которому обратились.
        entity_class_name : str
            Имя класса сущности.
        loaded_fields : frozenset[str]
            Множество полей, загруженных при создании.
    """

    def __init__(
        self,
        field_name: str,
        entity_class_name: str,
        loaded_fields: frozenset[str],
    ) -> None:
        """
        Инициализирует исключение.

        Аргументы:
            field_name: имя запрошенного поля.
            entity_class_name: имя класса сущности.
            loaded_fields: множество загруженных полей.
        """
        self.field_name: str = field_name
        self.entity_class_name: str = entity_class_name
        self.loaded_fields: frozenset[str] = loaded_fields

        sorted_fields = ", ".join(sorted(loaded_fields)) if loaded_fields else "(нет полей)"
        super().__init__(
            f"Поле '{field_name}' сущности '{entity_class_name}' не загружено. "
            f"Загруженные поля: {sorted_fields}. "
            f"Используйте полную загрузку или добавьте '{field_name}' в partial()."
        )


class RelationNotLoadedError(AttributeError):
    """
    Обращение к атрибуту связанной сущности, когда объект не загружен.

    Выбрасывается контейнерами связей One (CompositeOne, AggregateOne,
    AssociationOne) при попытке проксирования атрибута на entity, когда
    entity is None (менеджер загрузил только id). Также выбрасывается
    контейнерами Many при попытке итерации или индексного доступа,
    когда entities пуст.

    Наследует AttributeError по той же причине, что и FieldNotLoadedError:
    семантически это ошибка доступа к атрибуту, а hasattr() должен
    возвращать False для недоступных атрибутов.

    Это НЕ lazy-loading. Контейнер хранит id связанной сущности, но
    полный объект не загружен. Никаких скрытых запросов к хранилищу.
    Для загрузки объекта нужно явно обратиться к менеджеру.

    Атрибуты:
        container_class_name : str
            Имя класса контейнера связи (например, "AssociationOne").
        attribute_name : str
            Имя запрошенного атрибута (например, "name", "[0]", "__iter__").
        entity_id : Any
            Идентификатор связанной сущности (или кортеж id для Many).
            Включается в сообщение для диагностики.
    """

    def __init__(
        self,
        container_class_name: str,
        attribute_name: str,
        entity_id: Any,
    ) -> None:
        """
        Инициализирует исключение.

        Аргументы:
            container_class_name: имя класса контейнера связи.
            attribute_name: имя запрошенного атрибута.
            entity_id: идентификатор связанной сущности (или кортеж).
        """
        self.container_class_name: str = container_class_name
        self.attribute_name: str = attribute_name
        self.entity_id: Any = entity_id

        super().__init__(
            f"Объект связи в {container_class_name} не загружен (id={entity_id!r}). "
            f"Обращение к '{attribute_name}' невозможно — загружен только идентификатор. "
            f"Загрузите связанную сущность через менеджер."
        )


class EntityDecoratorError(TypeError):
    """
    Ошибка декоратора @entity.

    Выбрасывается при нарушении контракта декоратора:
    - Декоратор применён не к классу.
    - Класс не наследует EntityGateHost.
    - Параметр description не является строкой или пуст.
    - Параметр domain не является подклассом BaseDomain и не None.

    Наследует TypeError, потому что ошибки декоратора обнаруживаются
    на этапе определения класса (import-time) и являются ошибками
    разработчика, а не пользовательских данных.
    """

    pass


class LifecycleValidationError(Exception):
    """
    Нарушение целостности конечного автомата Lifecycle.

    Выбрасывается координатором сущностей (EntityCoordinator) при
    сборке метаданных, когда Lifecycle сущности не проходит проверки
    целостности.

    Восемь проверок целостности:
    1. Каждое состояние завершено флагом (.initial()/.intermediate()/.final()).
    2. Есть хотя бы одно начальное состояние.
    3. Есть хотя бы одно финальное состояние.
    4. Финальные состояния не имеют переходов.
    5. Все цели переходов существуют как объявленные состояния.
    6. Каждое не-финальное состояние имеет хотя бы один переход.
    7. Из каждого начального состояния достижимо хотя бы одно финальное.
    8. Каждое не-initial состояние является целью хотя бы одного перехода.

    Атрибуты:
        entity_name : str
            Имя класса сущности, содержащей невалидный Lifecycle.
        field_name : str
            Имя поля Lifecycle в сущности.
        details : str
            Детальное описание нарушения.
    """

    def __init__(
        self,
        entity_name: str,
        field_name: str,
        details: str,
    ) -> None:
        """
        Инициализирует исключение.

        Аргументы:
            entity_name: имя класса сущности.
            field_name: имя поля Lifecycle.
            details: описание нарушения.
        """
        self.entity_name: str = entity_name
        self.field_name: str = field_name
        self.details: str = details

        super().__init__(
            f"Ошибка Lifecycle '{field_name}' в сущности '{entity_name}': {details}"
        )
