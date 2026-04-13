# src/action_machine/dependencies/dependency_factory.py
"""
DependencyFactory — stateless-фабрика для создания экземпляров зависимостей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyFactory принимает кортеж DependencyInfo (из снимка ``depends``
через ``GateCoordinator.get_snapshot(cls, \"depends\")`` или
``cached_dependency_factory(coordinator, cls)``).
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
ПОДДЕРЖКА ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Метод resolve() принимает параметр rollup: bool = False. При rollup=True
выполняется дополнительная проверка: если созданный экземпляр является
наследником BaseResourceManager, вызывается check_rollup_support().

Если менеджер не поддерживает rollup (например, Redis, HTTP-клиент),
метод check_rollup_support() выбрасывает RollupNotSupportedError
с информативным сообщением. Тестировщик узнаёт об этом немедленно,
а не через неожиданное поведение в логах.

Если менеджер поддерживает rollup (SqlConnectionManager и наследники),
check_rollup_support() возвращает True, и resolve() возвращает
экземпляр без изменений. Флаг rollup передаётся в конструктор
менеджера ВЫЗЫВАЮЩИМ КОДОМ при создании connections, а не фабрикой.

═══════════════════════════════════════════════════════════════════════════════
ВЛАДЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Кеш экземпляров ``DependencyFactory`` на координаторе ведёт
``cached_dependency_factory()`` (словарь на ``coordinator.__dict__``).
Кортеж зависимостей читается из снимка ``depends`` через
``coordinator.get_snapshot(cls, \"depends\")``.

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ПАРАМЕТРОВ В resolve()
═══════════════════════════════════════════════════════════════════════════════

Сигнатура: resolve(klass, *args, rollup=False, **kwargs). Аргументы *args
и **kwargs пробрасываются в factory(*args, **kwargs) или klass(*args, **kwargs).
Параметр rollup — именованный, не пробрасывается в фабрику/конструктор.

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТЫ ИНИЦИАЛИЗАЦИИ
═══════════════════════════════════════════════════════════════════════════════

Поддерживает два формата:
1. tuple[DependencyInfo, ...] — основной (из снимка ``depends`` координатора).
2. list[dict] — обратная совместимость (для старых тестов).
   Каждый dict: {"class": type, "factory": callable|None, "description": str}

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Через координатор (основной сценарий):
    factory = cached_dependency_factory(coordinator, CreateOrderAction)
    payment = factory.resolve(PaymentService)

    # С рантайм-параметрами:
    payment = factory.resolve(PaymentService, gateway="stripe")

    # С rollup — проверка поддержки для BaseResourceManager:
    db_service = factory.resolve(DbService, rollup=True)
    # Если DbService наследует BaseResourceManager и не поддерживает rollup:
    # → RollupNotSupportedError

    # Через ToolsBox в аспекте (аспект не знает о фабрике напрямую):
    payment = box.resolve(PaymentService)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from action_machine.resources.base_resource_manager import BaseResourceManager

if TYPE_CHECKING:
    from action_machine.graph.gate_coordinator import GateCoordinator


@dataclass(frozen=True)
class DependencyInfo:
    """
    Неизменяемая информация об одной зависимости действия.

    Создаётся декоратором @depends и сохраняется в cls._depends_info.
    Снимок строит ``DependencyIntentInspector`` (``collect_dependencies``).
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

    При rollup=True дополнительно проверяет, что экземпляры BaseResourceManager
    поддерживают режим автоотката через check_rollup_support().

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
                  (из снимка ``depends`` координатора).
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

    def resolve(self, klass: type, *args: Any, rollup: bool = False, **kwargs: Any) -> Any:
        """
        Создаёт и возвращает новый экземпляр зависимости.

        Каждый вызов создаёт новый объект. Кеширование отсутствует.
        Если нужен синглтон, используйте lambda-замыкание в @depends(factory=...).

        Порядок создания:
        1. Ищет DependencyInfo в _deps по классу.
        2. Если info.factory задана — вызывает info.factory(*args, **kwargs).
        3. Иначе — вызывает klass(*args, **kwargs).
        4. Если rollup=True и результат — BaseResourceManager:
           вызывает instance.check_rollup_support(). При неподдержке —
           RollupNotSupportedError.

        Аргументы:
            klass: класс зависимости (тот же, что передан в @depends).
            *args: позиционные аргументы для фабрики или конструктора.
            rollup: если True, проверяет поддержку rollup для экземпляров
                    BaseResourceManager. По умолчанию False.
            **kwargs: именованные аргументы для фабрики или конструктора.

        Возвращает:
            Новый экземпляр зависимости.

        Исключения:
            ValueError: если зависимость не объявлена через @depends.
            RollupNotSupportedError: если rollup=True и экземпляр
                BaseResourceManager не поддерживает rollup.
        """
        info = self._deps.get(klass)
        if info is None:
            available = list(self._deps.keys())
            raise ValueError(
                f"Dependency {klass.__name__} not declared in @depends. "
                f"Available: {available}"
            )

        if info.factory:
            instance = info.factory(*args, **kwargs)
        else:
            instance = klass(*args, **kwargs)

        # Проверка rollup-поддержки для ресурсных менеджеров
        if rollup and isinstance(instance, BaseResourceManager):
            instance.check_rollup_support()

        return instance

    def get_all_classes(self) -> list[type]:
        """Возвращает список всех зарегистрированных классов зависимостей."""
        return list(self._deps.keys())

    def has(self, klass: type) -> bool:
        """Проверяет, есть ли зависимость для данного класса."""
        return klass in self._deps


DEPENDENCY_FACTORY_CACHE_KEY = "_action_machine_dependency_factory_cache"


def cached_dependency_factory(
    coordinator: GateCoordinator,
    cls: type,
) -> DependencyFactory:
    """
    Возвращает (и кеширует на экземпляре координатора) ``DependencyFactory``
    для класса действия, используя снимок ``depends``.
    """
    if not coordinator.is_built:
        raise RuntimeError(
            "GateCoordinator is not built. Register inspectors and call build() first.",
        )
    cache: dict[type, DependencyFactory] = coordinator.__dict__.setdefault(
        DEPENDENCY_FACTORY_CACHE_KEY,
        {},
    )
    if cls not in cache:
        snap = coordinator.get_snapshot(cls, "depends")
        if snap is not None and hasattr(snap, "dependencies"):
            deps = snap.dependencies
        else:
            deps = ()
        cache[cls] = DependencyFactory(deps)
    return cache[cls]


def clear_dependency_factory_cache(coordinator: GateCoordinator) -> int:
    """Очищает кеш фабрик на координаторе; возвращает число удалённых записей."""
    raw = coordinator.__dict__.get(DEPENDENCY_FACTORY_CACHE_KEY)
    if not isinstance(raw, dict) or not raw:
        return 0
    n = len(raw)
    raw.clear()
    return n
