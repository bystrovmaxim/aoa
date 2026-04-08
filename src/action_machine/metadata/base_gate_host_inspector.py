# src/action_machine/metadata/base_gate_host_inspector.py
"""
BaseGateHostInspector — абстрактный базовый класс для всех инспекторов
гейтхостов системы ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseGateHostInspector определяет контракт, которому обязан следовать каждый
инспектор гейтхоста в системе ActionMachine.

Инспектор — это класс, который:
1. Знает, наследников какого маркерного миксина обходить (_target_mixin).
2. Умеет инспектировать каждого наследника и собирать данные для графа.
3. Регистрируется в координаторе (GateCoordinator).

Координатор при build() обходит зарегистрированные инспекторы, вызывает
inspect() для каждого подкласса маркера и строит граф.

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛЕНИЕ: МАРКЕР И ИНСПЕКТОР
═══════════════════════════════════════════════════════════════════════════════

Каждый гейтхост существует в двух ипостасях:

    Маркерный миксин (RoleGateHost, AspectGateHost, DependencyGateHost[T]...)
        Живёт в MRO класса BaseAction (или BaseEntity, BaseResourceManager).
        Разрешает применение соответствующего декоратора через issubclass.
        Не содержит логики инспекции. Не наследует BaseGateHostInspector.
        Не меняется при рефакторинге.

    Инспектор (RoleGateHostInspector, AspectGateHostInspector...)
        Наследует BaseGateHostInspector. Реализует inspect() и
        _build_payload(). Обходит наследников маркера через _target_mixin.
        Регистрируется в координаторе.

Связь между ними — поле _target_mixin инспектора. Инспектор знает,
наследников какого маркера обходить. Маркер не знает про инспектор.

═══════════════════════════════════════════════════════════════════════════════
ДВА ОБЯЗАТЕЛЬНЫХ МЕТОДА
═══════════════════════════════════════════════════════════════════════════════

Каждый инспектор реализует два абстрактных classmethod:

    inspect(target_cls) → FacetPayload | None
        Точка входа. Определяет, подходит ли класс этому инспектору.
        Два возможных результата:
        - FacetPayload — класс подходит, данные собраны.
        - None — класс не является субъектом этого инспектора.

    _build_payload(target_cls) → FacetPayload
        Собирает узел и рёбра. Читает атрибуты класса (_role_info,
        _depends_info, _meta_info и т.д.), формирует FacetPayload
        с использованием хелперов базового класса.

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛЕНИЕ ВАЛИДАЦИИ
═══════════════════════════════════════════════════════════════════════════════

Валидация выполняется на двух уровнях, каждый — в одном месте:

    Декораторы (@check_roles, @regular_aspect, @depends...)
        Проверяют аргументы при import-time: типы, пустоту, issubclass,
        дубликаты. Обнаруживают ошибки немедленно при определении класса.

    Координатор (GateCoordinator.build())
        Глобальные структурные проверки после сбора всех payload:
        уникальность ключей, ссылочная целостность рёбер, ацикличность
        структурных рёбер.

Инспектор НЕ содержит метода _validate(). Логика проверки не
размазывается между декоратором и инспектором.

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ
═══════════════════════════════════════════════════════════════════════════════

    inspect()        → проверяет ТОЛЬКО наличие данных (есть _role_info?)
    _build_payload() → читает данные, формирует payload

Это разделение гарантирует, что:
- inspect() работает быстро — только hasattr/getattr.
- _build_payload() формирует payload без побочных эффектов.

═══════════════════════════════════════════════════════════════════════════════
ХЕЛПЕРЫ
═══════════════════════════════════════════════════════════════════════════════

Базовый класс предоставляет пять хелперов, устраняющие дублирование
в каждом инспекторе:

    _make_node_name(target_cls, suffix="") → str
        Формирует имя узла "module.ClassName" или "module.ClassName.suffix".
        Префикс типа ("action:", "role:") НЕ добавляется — это делает
        координатор при формировании ключа.

    _make_edge(target_node_type, target_cls, edge_type,
               is_structural, edge_meta=()) → EdgeInfo
        Собирает EdgeInfo без ручного заполнения каждого поля.
        Имя цели формируется через _make_node_name(target_cls).

    _make_edge_by_name(target_node_type, target_name, edge_type,
                       is_structural, edge_meta=()) → EdgeInfo
        Аналог _make_edge для случаев, когда цель — не класс,
        а произвольное строковое имя (например, "context_field:user.user_id").

    _make_meta(**kwargs) → tuple[tuple[str, Any], ...]
        Конвертирует dict-синтаксис в иммутабельный tuple of tuples,
        пригодный для frozen dataclass.

    _collect_subclasses(mixin) → list[type]
        Рекурсивно собирает всех наследников маркерного миксина.
        Используется инспекторами в переопределённом
        _subclasses_recursive() для обхода наследников своего маркера.

═══════════════════════════════════════════════════════════════════════════════
ОБХОД НАСЛЕДНИКОВ
═══════════════════════════════════════════════════════════════════════════════

Метод _subclasses_recursive() определён в базовом классе и рекурсивно
собирает подклассы через __subclasses__(). Инспекторы переопределяют его,
чтобы обходить наследников _target_mixin, а не своих собственных:

    class RoleGateHostInspector(BaseGateHostInspector):
        _target_mixin = RoleGateHost

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_mixin)

Координатор вызывает _subclasses_recursive() при build() для каждого
зарегистрированного инспектора.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР РЕАЛИЗАЦИИ ИНСПЕКТОРА БЕЗ РЁБЕР
═══════════════════════════════════════════════════════════════════════════════

    class RoleGateHostInspector(BaseGateHostInspector):
        _target_mixin = RoleGateHost

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_mixin)

        @classmethod
        def inspect(cls, target_cls: type) -> FacetPayload | None:
            role_info = getattr(target_cls, "_role_info", None)
            if role_info is None:
                return None
            return cls._build_payload(target_cls)

        @classmethod
        def _build_payload(cls, target_cls: type) -> FacetPayload:
            return FacetPayload(
                node_type="role",
                node_name=cls._make_node_name(target_cls),
                node_class=target_cls,
                node_meta=cls._make_meta(spec=target_cls._role_info["spec"]),
            )

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР РЕАЛИЗАЦИИ ИНСПЕКТОРА С РЁБРАМИ
═══════════════════════════════════════════════════════════════════════════════

    class DependencyGateHostInspector(BaseGateHostInspector):
        _target_mixin = DependencyGateHost

        @classmethod
        def _subclasses_recursive(cls) -> list[type]:
            return cls._collect_subclasses(cls._target_mixin)

        @classmethod
        def inspect(cls, target_cls: type) -> FacetPayload | None:
            depends_info = getattr(target_cls, "_depends_info", None)
            if not depends_info:
                return None
            return cls._build_payload(target_cls)

        @classmethod
        def _build_payload(cls, target_cls: type) -> FacetPayload:
            edges = tuple(
                cls._make_edge(
                    target_node_type="dependency",
                    target_cls=dep_info.cls,
                    edge_type="depends",
                    is_structural=True,
                )
                for dep_info in target_cls._depends_info
            )
            return FacetPayload(
                node_type="action",
                node_name=cls._make_node_name(target_cls),
                node_class=target_cls,
                edges=edges,
            )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from action_machine.metadata.payload import EdgeInfo, FacetPayload


class BaseGateHostInspector(ABC):
    """
    Абстрактный базовый класс для всех инспекторов гейтхостов.

    Определяет контракт из двух абстрактных classmethod (inspect,
    _build_payload) и предоставляет пять хелперов для формирования
    FacetPayload и EdgeInfo без дублирования кода в каждом инспекторе.

    Все методы — classmethod или staticmethod. Инспектор не хранит
    состояния и не требует создания экземпляра. Группировка в класс
    обеспечивает пространство имён, наследование хелперов и проверку
    контракта через ABC.

    Координатор (GateCoordinator) при build() вызывает:
    1. inspector._subclasses_recursive() — получить всех наследников маркера.
    2. inspector.inspect(target_cls) — инспектировать каждого наследника.
    """

    # ═══════════════════════════════════════════════════════════════════
    # Обязательный контракт (два абстрактных метода)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    @abstractmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """
        Определяет, подходит ли класс этому инспектору, и собирает данные.

        Точка входа, вызываемая координатором для каждого подкласса
        маркерного миксина. Реализация типичного inspect():

            1. Проверить наличие данных (hasattr/getattr).
            2. Если данных нет → return None.
            3. Вызвать _build_payload() → FacetPayload.
            4. Вернуть payload.

        Аргументы:
            target_cls: класс для инспекции. Найден через
                        _subclasses_recursive() — является подклассом
                        маркерного миксина (_target_mixin).

        Возвращает:
            FacetPayload — класс подходит, данные собраны.
            None — класс не является субъектом этого инспектора
                   (нет соответствующих атрибутов/декораторов).
        """
        ...

    @classmethod
    @abstractmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """
        Собирает FacetPayload из атрибутов класса.

        Читает данные (_role_info, _depends_info и т.д.), формирует
        узел и рёбра с использованием хелперов базового класса:
        _make_node_name, _make_edge, _make_edge_by_name, _make_meta.

        Аргументы:
            target_cls: класс, прошедший проверку наличия данных
                        в inspect().

        Возвращает:
            FacetPayload — полное описание узла с рёбрами.
        """
        ...

    # ═══════════════════════════════════════════════════════════════════
    # Хелперы для _build_payload
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def _make_node_name(cls, target_cls: type, suffix: str = "") -> str:
        """
        Формирует имя узла из модуля и имени класса.

        Формат: "module.ClassName" или "module.ClassName.suffix".
        Если модуль "__main__" или отсутствует — только "ClassName".

        Префикс типа ("action:", "role:") НЕ добавляется. Полный ключ
        "node_type:node_name" собирает координатор при коммите.

        Аргументы:
            target_cls: класс, для которого формируется имя.
            suffix: опциональный суффикс, добавляемый через точку.
                    Используется для дочерних узлов: аспектов,
                    чекеров, полей сущностей.
                    Пустая строка — суффикс не добавляется.

        Возвращает:
            str — имя узла.

        Примеры:
            _make_node_name(CreateOrderAction)
            → "myapp.orders.CreateOrderAction"

            _make_node_name(CreateOrderAction, "validate_aspect")
            → "myapp.orders.CreateOrderAction.validate_aspect"

            _make_node_name(OrderEntity, "amount")
            → "myapp.domain.OrderEntity.amount"
        """
        module = getattr(target_cls, "__module__", None)
        if module and module != "__main__":
            name = f"{module}.{target_cls.__qualname__}"
        else:
            name = target_cls.__qualname__
        if suffix:
            return f"{name}.{suffix}"
        return name

    @classmethod
    def _make_edge(
        cls,
        target_node_type: str,
        target_cls: type,
        edge_type: str,
        is_structural: bool,
        edge_meta: tuple[tuple[str, Any], ...] = (),
    ) -> EdgeInfo:
        """
        Собирает EdgeInfo с автоматическим формированием имени цели.

        Имя целевого узла формируется через _make_node_name(target_cls).
        Используется когда цель ребра — класс Python.

        Аргументы:
            target_node_type: тип целевого узла ("action", "entity",
                              "domain", "dependency" и т.д.).
            target_cls: класс, являющийся целью ребра.
            edge_type: тип ребра ("depends", "connection", "has_aspect",
                       "belongs_to" и т.д.).
            is_structural: True — структурное ребро (циклы запрещены).
                           False — информационное ребро (циклы допустимы).
            edge_meta: дополнительные метаданные ребра.
                       Пустой tuple по умолчанию.

        Возвращает:
            EdgeInfo — описание ребра.

        Пример:
            cls._make_edge(
                target_node_type="dependency",
                target_cls=PaymentService,
                edge_type="depends",
                is_structural=True,
            )
        """
        return EdgeInfo(
            target_node_type=target_node_type,
            target_name=cls._make_node_name(target_cls),
            edge_type=edge_type,
            is_structural=is_structural,
            edge_meta=edge_meta,
        )

    @classmethod
    def _make_edge_by_name(
        cls,
        target_node_type: str,
        target_name: str,
        edge_type: str,
        is_structural: bool,
        edge_meta: tuple[tuple[str, Any], ...] = (),
    ) -> EdgeInfo:
        """
        Собирает EdgeInfo с произвольным строковым именем цели.

        Используется когда цель ребра — не класс Python, а строковый
        идентификатор. Например, узлы контекстных полей
        ("context_field:user.user_id") или доменов ("domain:orders").

        Аргументы:
            target_node_type: тип целевого узла.
            target_name: строковое имя целевого узла.
            edge_type: тип ребра.
            is_structural: структурное или информационное.
            edge_meta: дополнительные метаданные ребра.

        Возвращает:
            EdgeInfo — описание ребра.

        Пример:
            cls._make_edge_by_name(
                target_node_type="context_field",
                target_name="user.user_id",
                edge_type="requires_context",
                is_structural=False,
            )
        """
        return EdgeInfo(
            target_node_type=target_node_type,
            target_name=target_name,
            edge_type=edge_type,
            is_structural=is_structural,
            edge_meta=edge_meta,
        )

    @classmethod
    def _make_meta(cls, **kwargs: Any) -> tuple[tuple[str, Any], ...]:
        """
        Конвертирует именованные аргументы в иммутабельный tuple of tuples.

        Frozen dataclass требует хешируемые поля. dict не хешируем.
        Этот хелпер позволяет инспекторам использовать удобный
        dict-синтаксис (kwargs) при создании метаданных, получая
        на выходе иммутабельную структуру.

        Координатор конвертирует tuple of tuples обратно в dict
        при коммите: dict(node_meta).

        Аргументы:
            **kwargs: произвольные пары ключ-значение метаданных.

        Возвращает:
            tuple[tuple[str, Any], ...] — иммутабельные метаданные.

        Пример:
            cls._make_meta(spec="admin", description="Администратор")
            → (("spec", "admin"), ("description", "Администратор"))

            cls._make_meta()
            → ()
        """
        return tuple(kwargs.items())

    # ═══════════════════════════════════════════════════════════════════
    # Обход наследников
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _collect_subclasses(mixin: type) -> list[type]:
        """
        Рекурсивно собирает всех наследников маркерного миксина.

        Обходит дерево наследования через Python-механизм __subclasses__(),
        который автоматически регистрирует подклассы при определении.
        Никакой ручной регистрации не требуется.

        Используется инспекторами в переопределённом _subclasses_recursive()
        для обхода наследников своего маркера (_target_mixin), а не
        наследников самого инспектора.

        Порядок обхода: depth-first. Прямые подклассы добавляются
        перед их потомками.

        Аргументы:
            mixin: маркерный миксин, наследников которого нужно собрать.
                   Например: RoleGateHost, AspectGateHost, EntityGateHost.

        Возвращает:
            list[type] — все прямые и транзитивные подклассы миксина.
                         Пустой список если у миксина нет наследников.

        Пример:
            class RoleGateHost: ...
            class BaseAction(RoleGateHost): ...
            class CreateOrderAction(BaseAction): ...

            BaseGateHostInspector._collect_subclasses(RoleGateHost)
            → [BaseAction, CreateOrderAction]
        """
        result: list[type] = []
        for sub in mixin.__subclasses__():
            result.append(sub)
            result.extend(BaseGateHostInspector._collect_subclasses(sub))
        return result

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """
        Рекурсивно собирает всех наследников для инспекции.

        Базовая реализация обходит наследников самого инспектора.
        Конкретные инспекторы переопределяют этот метод, чтобы
        обходить наследников _target_mixin:

            @classmethod
            def _subclasses_recursive(cls) -> list[type]:
                return cls._collect_subclasses(cls._target_mixin)

        Координатор вызывает этот метод при build() для каждого
        зарегистрированного инспектора.

        Возвращает:
            list[type] — все классы для инспекции.
        """
        result: list[type] = []
        for subclass in cls.__subclasses__():
            result.append(subclass)
            if hasattr(subclass, "_subclasses_recursive"):
                result.extend(subclass._subclasses_recursive())
        return result
