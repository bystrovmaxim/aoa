# src/action_machine/dependencies/dependency_factory.py
"""
DependencyFactory — stateless-фабрика для создания экземпляров зависимостей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyFactory принимает кортеж DependencyInfo (из ClassMetadata.dependencies)
и предоставляет метод resolve() для создания экземпляров зависимостей,
объявленных через декоратор @depends.

═══════════════════════════════════════════════════════════════════════════════
STATELESS-ДИЗАЙН
═══════════════════════════════════════════════════════════════════════════════

Фабрика не хранит кеш экземпляров. Каждый вызов resolve() создаёт новый
экземпляр через factory-функцию или конструктор по умолчанию. Это превращает
фабрику в чистую функцию: один и тот же вход (класс зависимости) всегда
порождает новый экземпляр по одним и тем же правилам.

Синглтоны реализуются пользователем через lambda-замыкание:

    _shared = PaymentService(gateway="production")

    @depends(PaymentService, factory=lambda: _shared)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

Фреймворк предоставляет механизм (параметр factory), пользователь
выбирает политику (синглтон, per-request, пул, любой внешний DI-контейнер).

═══════════════════════════════════════════════════════════════════════════════
ВНУТРЕННЕЕ УСТРОЙСТВО
═══════════════════════════════════════════════════════════════════════════════

Фабрика строит внутренний словарь dict[type, DependencyInfo] из входного
кортежа при инициализации. Словарь не изменяется после создания.

Промежуточный DependencyGate (отдельный класс-реестр с методами
register/unregister/freeze) удалён за ненадобностью: фабрика иммутабельна
после создания, заморозка не нужна, удаление зависимостей не используется.

═══════════════════════════════════════════════════════════════════════════════
ВЛАДЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Экземпляры DependencyFactory создаются и хранятся в GateCoordinator
(метод get_factory()). Координатор передаёт metadata.dependencies напрямую
в конструктор фабрики. Поскольку фабрика stateless, один экземпляр
безопасно разделяется между всеми вызовами run() для одного класса действия.

ActionProductMachine и ActionTestMachine получают фабрику через
coordinator.get_factory(action.__class__) и не хранят собственный кеш.

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ПАРАМЕТРОВ В resolve()
═══════════════════════════════════════════════════════════════════════════════

Сигнатура: resolve(klass, *args, **kwargs). Аргументы пробрасываются
в factory(*args, **kwargs) или klass(*args, **kwargs). Без аргументов
поведение идентично прежнему — полная обратная совместимость.

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТЫ ИНИЦИАЛИЗАЦИИ
═══════════════════════════════════════════════════════════════════════════════

Поддерживает два формата:
1. tuple[DependencyInfo, ...] — основной (из ClassMetadata.dependencies).
2. list[dict] — обратная совместимость (для старых тестов).
   Каждый dict: {"class": type, "factory": callable|None, "description": str}

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Через координатор (основной сценарий):
    factory = coordinator.get_factory(CreateOrderAction)
    payment = factory.resolve(PaymentService)

    # С рантайм-параметрами:
    payment = factory.resolve(PaymentService, gateway="stripe")

    # Через ToolsBox в аспекте (аспект не знает о фабрике напрямую):
    payment = box.resolve(PaymentService)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DependencyInfo:
    """
    Неизменяемая информация об одной зависимости действия.

    Создаётся декоратором @depends и сохраняется в cls._depends_info.
    MetadataBuilder собирает их в ClassMetadata.dependencies (tuple).
    GateCoordinator передаёт этот кортеж в DependencyFactory.

    Атрибуты:
        cls: класс зависимости (тип, запрашиваемый через box.resolve).
             Например: PaymentService, NotificationService.
        factory: опциональная фабрика для создания экземпляра.
                 Если None — используется конструктор по умолчанию klass().
                 Для синглтонов: factory=lambda: shared_instance.
                 Для параметризованных: factory=lambda env: BankClient(env).
        description: текстовое описание зависимости для документации
                     и интроспекции. Отображается в графе координатора.
    """
    cls: type
    factory: Callable[..., Any] | None = None
    description: str = ""


class DependencyFactory:
    """
    Stateless-фабрика зависимостей для действий.

    Каждый вызов resolve() создаёт новый экземпляр через factory-функцию
    или конструктор по умолчанию. Кеш экземпляров отсутствует.

    Внутренний словарь _deps строится из входного кортежа при инициализации
    и не модифицируется после этого.

    Атрибуты:
        _deps : dict[type, DependencyInfo]
            Словарь для быстрого поиска по классу зависимости.
            Строится один раз в __init__.
    """

    def __init__(self, dependencies: tuple[Any, ...] | list[dict[str, Any]]) -> None:
        """
        Инициализирует фабрику.

        Аргументы:
            dependencies:
                - tuple[DependencyInfo, ...] — основной формат
                  (из ClassMetadata.dependencies, передаётся GateCoordinator).
                - list[dict] — обратная совместимость для тестов.
                  Каждый dict: {"class": type, "factory": callable|None,
                  "description": str}
        """
        if isinstance(dependencies, (tuple, list)) and dependencies and isinstance(dependencies[0], dict):
            self._deps: dict[type, DependencyInfo] = self._build_from_dicts(list(dependencies))
        else:
            self._deps = self._build_from_infos(dependencies)

    @staticmethod
    def _build_from_infos(infos: tuple[Any, ...] | list[Any]) -> dict[type, DependencyInfo]:
        """
        Строит словарь из кортежа DependencyInfo.

        Аргументы:
            infos: кортеж или список DependencyInfo.

        Возвращает:
            dict[type, DependencyInfo].
        """
        result: dict[type, DependencyInfo] = {}
        for info in infos:
            result[info.cls] = info
        return result

    @staticmethod
    def _build_from_dicts(dicts: list[dict[str, Any]]) -> dict[type, DependencyInfo]:
        """
        Строит словарь из списка словарей (обратная совместимость).

        Аргументы:
            dicts: список словарей с ключами "class", "factory", "description".

        Возвращает:
            dict[type, DependencyInfo].
        """
        result: dict[type, DependencyInfo] = {}
        for info_dict in dicts:
            info = DependencyInfo(
                cls=info_dict["class"],
                factory=info_dict.get("factory"),
                description=info_dict.get("description", ""),
            )
            result[info.cls] = info
        return result

    def resolve(self, klass: type, *args: Any, **kwargs: Any) -> Any:
        """
        Создаёт и возвращает новый экземпляр зависимости.

        Каждый вызов создаёт новый объект. Кеширование отсутствует.
        Если нужен синглтон, используйте lambda-замыкание в @depends(factory=...).

        Порядок создания:
        1. Ищет DependencyInfo в _deps по классу.
        2. Если info.factory задана — вызывает info.factory(*args, **kwargs).
        3. Иначе — вызывает klass(*args, **kwargs).

        Аргументы:
            klass: класс зависимости (тот же, что передан в @depends).
            *args: позиционные аргументы для фабрики или конструктора.
            **kwargs: именованные аргументы для фабрики или конструктора.

        Возвращает:
            Новый экземпляр зависимости.

        Исключения:
            ValueError: если зависимость не объявлена через @depends.
        """
        info = self._deps.get(klass)
        if info is None:
            available = list(self._deps.keys())
            raise ValueError(
                f"Dependency {klass.__name__} not declared in @depends. "
                f"Available: {available}"
            )

        if info.factory:
            return info.factory(*args, **kwargs)

        return klass(*args, **kwargs)

    def get_all_classes(self) -> list[type]:
        """Возвращает список всех зарегистрированных классов зависимостей."""
        return list(self._deps.keys())

    def has(self, klass: type) -> bool:
        """Проверяет, есть ли зависимость для данного класса."""
        return klass in self._deps
