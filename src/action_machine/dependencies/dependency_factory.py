# src/action_machine/dependencies/dependency_factory.py
"""
DependencyFactory — stateless-фабрика для создания экземпляров зависимостей действий.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DependencyFactory оборачивает замороженный DependencyGate и предоставляет
метод resolve() для создания экземпляров зависимостей, объявленных через
декоратор @depends.

═══════════════════════════════════════════════════════════════════════════════
STATELESS-ДИЗАЙН
═══════════════════════════════════════════════════════════════════════════════

Фабрика НЕ хранит кеш экземпляров (_instances удалён). Каждый вызов
resolve() создаёт НОВЫЙ экземпляр зависимости через фабрику (info.factory)
или конструктор по умолчанию (klass()).

Это превращает фабрику в чистую функцию над замороженным DependencyGate:
один и тот же вход (класс зависимости) всегда порождает новый экземпляр
по одним и тем же правилам.

Отсутствие кеша не лишает пользователя возможности создавать синглтоны.
Если зависимость должна быть синглтоном, пользователь реализует это
через lambda-замыкание в параметре factory декоратора @depends:

    # Создаём экземпляр один раз вне класса действия
    _payment_service = PaymentService(gateway="production")

    @depends(PaymentService, factory=lambda: _payment_service, description="Синглтон")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

Фреймворк предоставляет механизм (параметр factory), пользователь
выбирает политику (синглтон, per-request, пул, любой внешний DI-контейнер).

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ПАРАМЕТРОВ В resolve()
═══════════════════════════════════════════════════════════════════════════════

Сигнатура resolve() расширена до resolve(klass, *args, **kwargs).
Аргументы пробрасываются в info.factory(*args, **kwargs) или
klass(*args, **kwargs). При вызове без аргументов поведение идентично
прежнему — полная обратная совместимость.

Это позволяет аспектам передавать рантайм-параметры при создании
зависимостей. Lambda-фабрика в @depends определяет контракт (какие
параметры принимает), аспект передаёт значения при вызове box.resolve().

═══════════════════════════════════════════════════════════════════════════════
ВЛАДЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Экземпляры DependencyFactory создаются и хранятся в GateCoordinator
(метод get_factory()). Поскольку фабрика stateless, один экземпляр
безопасно разделяется между всеми вызовами run() для одного класса
действия.

ActionProductMachine и ActionTestMachine получают фабрику через
coordinator.get_factory(action.__class__) и НЕ хранят собственный кеш.

═══════════════════════════════════════════════════════════════════════════════
ФОРМАТЫ ИНИЦИАЛИЗАЦИИ
═══════════════════════════════════════════════════════════════════════════════

Поддерживает два формата:
1. DependencyGate — основной формат (из координатора).
2. list[dict] — обратная совместимость (для тестов и старого кода).
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

from typing import Any

from .dependency_gate import DependencyGate, DependencyInfo


class DependencyFactory:
    """
    Stateless-фабрика зависимостей для действий.

    Каждый вызов resolve() создаёт новый экземпляр зависимости через
    фабрику (info.factory) или конструктор по умолчанию (klass()).
    Кеш экземпляров отсутствует — фабрика является чистой функцией
    над замороженным DependencyGate.

    Если нужен синглтон, пользователь оборачивает экземпляр в lambda:
        @depends(Service, factory=lambda: shared_instance)

    Атрибуты:
        _gate : DependencyGate
            Замороженный шлюз с информацией о зависимостях (класс,
            фабрика, описание). Используется для поиска DependencyInfo
            по классу при вызове resolve().
    """

    def __init__(self, gate: DependencyGate | list[dict[str, Any]]) -> None:
        """
        Инициализирует фабрику.

        Аргументы:
            gate: DependencyGate, содержащий информацию о зависимостях,
                  или list[dict] для обратной совместимости.
                  Каждый dict в списке:
                  {"class": type, "factory": callable|None, "description": str}

        Исключения:
            TypeError: если gate не является DependencyGate или list[dict].
        """
        if isinstance(gate, DependencyGate):
            self._gate: DependencyGate = gate
        elif isinstance(gate, list):
            self._gate = self._gate_from_list(gate)
        else:
            raise TypeError(
                f"DependencyFactory expects DependencyGate or list[dict], "
                f"got {type(gate).__name__}"
            )

    @staticmethod
    def _gate_from_list(deps_info: list[dict[str, Any]]) -> DependencyGate:
        """
        Создаёт DependencyGate из списка словарей (обратная совместимость).

        Каждый словарь конвертируется в DependencyInfo и регистрируется
        в новом DependencyGate, который затем замораживается.

        Аргументы:
            deps_info: список словарей, каждый содержит:
                - "class": тип зависимости
                - "factory": опциональная фабрика (callable или None)
                - "description": описание (строка)

        Возвращает:
            Заполненный и замороженный DependencyGate.
        """
        gate = DependencyGate()
        for info_dict in deps_info:
            info = DependencyInfo(
                cls=info_dict["class"],
                factory=info_dict.get("factory"),
                description=info_dict.get("description", ""),
            )
            gate.register(info)
        gate.freeze()
        return gate

    def resolve(self, klass: type, *args: Any, **kwargs: Any) -> Any:
        """
        Создаёт и возвращает новый экземпляр зависимости указанного класса.

        Каждый вызов создаёт НОВЫЙ экземпляр. Кеширование отсутствует.
        Если нужен синглтон, используйте lambda-замыкание в параметре
        factory декоратора @depends.

        Порядок создания:
        1. Ищет DependencyInfo в шлюзе по классу.
        2. Если info.factory задана — вызывает info.factory(*args, **kwargs).
        3. Иначе — вызывает klass(*args, **kwargs).

        Аргументы *args и **kwargs пробрасываются в фабрику или конструктор.
        При вызове без аргументов поведение идентично прежнему —
        полная обратная совместимость.

        Аргументы:
            klass: класс зависимости (тот же, что передан в @depends).
            *args: позиционные аргументы, пробрасываемые в фабрику
                   или конструктор.
            **kwargs: именованные аргументы, пробрасываемые в фабрику
                      или конструктор.

        Возвращает:
            Новый экземпляр зависимости.

        Исключения:
            ValueError: если зависимость не объявлена в шлюзе (@depends).
        """
        info: DependencyInfo | None = self._gate.get_by_class(klass)
        if info is None:
            raise ValueError(
                f"Dependency {klass.__name__} not declared in @depends. "
                f"Available: {self._gate.get_all_classes()}"
            )

        if info.factory:
            return info.factory(*args, **kwargs)

        return klass(*args, **kwargs)
