# src/action_machine/core/gate_coordinator.py
"""
Модуль: GateCoordinator — центральный реестр метаданных и фабрик зависимостей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

GateCoordinator — единственная точка доступа к метаданным классов и фабрикам
зависимостей во всей системе ActionMachine. Он отвечает за:

1. ЛЕНИВУЮ СБОРКУ МЕТАДАННЫХ: при первом обращении к классу координатор
   вызывает MetadataBuilder.build(cls), получает ClassMetadata и кеширует его.
   Повторные обращения возвращают кешированный объект мгновенно.

2. КЕШИРОВАНИЕ МЕТАДАННЫХ: каждый класс собирается ровно один раз. Кеш
   привязан к id(cls), что гарантирует корректность при наличии одноимённых
   классов из разных модулей.

3. ВЛАДЕНИЕ ФАБРИКАМИ ЗАВИСИМОСТЕЙ: координатор при сборке метаданных
   дополнительно строит DependencyGate из metadata.dependencies,
   замораживает его и оборачивает в DependencyFactory. Фабрика хранится
   рядом с метаданными. Поскольку DependencyFactory stateless (не хранит
   кеш экземпляров), один экземпляр безопасно разделяется между всеми
   вызовами run() для одного класса действия.

4. ЕДИНООБРАЗНЫЙ ДОСТУП: вместо разрозненных обращений к cls._depends_info,
   cls._role_info и т.д. — один вызов coordinator.get(cls) возвращает
   полный снимок. Для фабрик — coordinator.get_factory(cls).

5. ИНВАЛИДАЦИЯ (опционально): метод invalidate(cls) удаляет кеш метаданных
   и фабрику для класса. Используется в тестах или при динамическом
   переопределении декораторов.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌───────────────────────┐
    │  ActionProductMachine  │
    │  ActionTestMachine     │        потребители
    │  PluginCoordinator     │
    └──────────┬────────────┘
               │
               │  coordinator.get(cls)          → ClassMetadata
               │  coordinator.get_factory(cls)  → DependencyFactory
               ▼
    ┌──────────────────────────┐
    │  GateCoordinator          │
    │                          │
    │  _cache: dict            │──── id(cls) → ClassMetadata
    │  _factory_cache: dict    │──── id(cls) → DependencyFactory
    │  _class_map: dict        │──── id(cls) → cls
    │                          │
    └──────────┬───────────────┘
               │  cache miss → MetadataBuilder.build(cls)
               │            → DependencyGate + DependencyFactory
               ▼
    ┌──────────────────┐
    │  MetadataBuilder  │
    └──────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. КООРДИНАТОР — ЕДИНСТВЕННЫЙ ВЛАДЕЛЕЦ: метаданных, фабрик и графа
   зависимостей. Машина НЕ хранит собственных кешей фабрик.

2. ПОСЛЕ ЗАВЕРШЕНИЯ РЕГИСТРАЦИИ КООРДИНАТОР НЕИЗМЕНЯЕМ: все данные
   создаются лениво при первом обращении и затем не меняются.
   Инвалидация предназначена только для тестов.

3. КООРДИНАТОР НЕ ЗНАЕТ О БИЗНЕС-ЛОГИКЕ: он не проверяет роли,
   не резолвит зависимости, не запускает аспекты. Он только хранит
   и отдаёт метаданные и фабрики.

4. ПОТОКОБЕЗОПАСНОСТЬ: GateCoordinator не использует блокировки, потому что
   в asyncio-среде код выполняется в одном потоке.

5. ОТКРЫТ ДЛЯ РАСШИРЕНИЯ, ЗАКРЫТ ДЛЯ МОДИФИКАЦИИ (OCP): новый декоратор
   → новое поле в ClassMetadata → новый _collect_* в MetadataBuilder.
   GateCoordinator не затрагивается.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

    coordinator = GateCoordinator()

    # Получение метаданных:
    meta = coordinator.get(CreateOrderAction)
    print(meta.role.spec)
    print(meta.dependencies)

    # Получение фабрики зависимостей:
    factory = coordinator.get_factory(CreateOrderAction)
    payment = factory.resolve(PaymentService)

    # Повторный вызов — из кеша:
    meta2 = coordinator.get(CreateOrderAction)
    assert meta is meta2

    factory2 = coordinator.get_factory(CreateOrderAction)
    assert factory is factory2

    # Инвалидация (для тестов):
    coordinator.invalidate(CreateOrderAction)
"""

from __future__ import annotations

from typing import Any

from action_machine.core.class_metadata import ClassMetadata, RoleMeta
from action_machine.core.metadata_builder import MetadataBuilder
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.dependencies.dependency_gate import DependencyGate


class GateCoordinator:
    """
    Центральный реестр метаданных и фабрик зависимостей.

    Хранит собранные метаданные классов и stateless-фабрики зависимостей,
    предоставляя к ним доступ через get() и get_factory(). При первом
    обращении к классу автоматически вызывает MetadataBuilder.build()
    и кеширует результат. Для классов с зависимостями дополнительно
    строит DependencyGate, замораживает его и оборачивает в DependencyFactory.

    Экземпляр GateCoordinator создаётся явно и передаётся в конструктор
    ActionProductMachine или ActionTestMachine через dependency injection.
    Глобальных синглтонов не существует — каждый экземпляр машины владеет
    своим координатором (или разделяет его с другими машинами осознанно).

    Атрибуты:
        _cache : dict[int, ClassMetadata]
            Кеш метаданных. Ключ — id(cls), значение — ClassMetadata.

        _factory_cache : dict[int, DependencyFactory]
            Кеш stateless-фабрик зависимостей. Ключ — id(cls), значение —
            DependencyFactory. Фабрика создаётся из metadata.dependencies
            при первом вызове get_factory(). Поскольку DependencyFactory
            не хранит состояния (кеш экземпляров удалён), один экземпляр
            безопасно разделяется между всеми вызовами run().

        _class_map : dict[int, type]
            Обратная карта id(cls) → cls. Нужна для методов инспекции.
    """

    def __init__(self) -> None:
        """
        Создаёт пустой координатор.

        Кеши заполняются лениво — при первом вызове get() и get_factory().
        """
        self._cache: dict[int, ClassMetadata] = {}
        self._factory_cache: dict[int, DependencyFactory] = {}
        self._class_map: dict[int, type] = {}

    # ─────────────────────────────────────────────────────────────────────
    # Основной API: метаданные
    # ─────────────────────────────────────────────────────────────────────

    def get(self, cls: type) -> ClassMetadata:
        """
        Возвращает ClassMetadata для указанного класса.

        При первом вызове собирает метаданные через MetadataBuilder.build()
        и кеширует результат. Повторные вызовы возвращают кешированный объект.

        Аргументы:
            cls: класс, метаданные которого нужно получить.

        Возвращает:
            ClassMetadata — иммутабельный снимок метаданных класса.

        Исключения:
            TypeError: если cls не является классом.
            ValueError: если MetadataBuilder обнаруживает структурные ошибки.
        """
        if not isinstance(cls, type):
            raise TypeError(
                f"GateCoordinator.get() ожидает класс (type), "
                f"получен {type(cls).__name__}: {cls!r}"
            )

        class_id = id(cls)

        if class_id not in self._cache:
            metadata = MetadataBuilder.build(cls)
            self._cache[class_id] = metadata
            self._class_map[class_id] = cls

        return self._cache[class_id]

    def register(self, cls: type) -> ClassMetadata:
        """
        Явно регистрирует класс в координаторе.

        Эквивалентен get(), но семантически выражает намерение
        «зарегистрировать класс заранее».

        Аргументы:
            cls: класс для регистрации.

        Возвращает:
            ClassMetadata — собранные метаданные.
        """
        return self.get(cls)

    # ─────────────────────────────────────────────────────────────────────
    # Основной API: фабрики зависимостей
    # ─────────────────────────────────────────────────────────────────────

    def get_factory(self, cls: type) -> DependencyFactory:
        """
        Возвращает DependencyFactory для указанного класса.

        При первом вызове:
        1. Получает ClassMetadata через get() (лениво собирает, если нужно).
        2. Строит DependencyGate из metadata.dependencies.
        3. Замораживает DependencyGate.
        4. Оборачивает в DependencyFactory и кеширует.

        Повторные вызовы возвращают кешированную фабрику. Поскольку
        DependencyFactory stateless (не хранит кеш экземпляров), один
        экземпляр безопасно разделяется между всеми вызовами run()
        для одного класса действия.

        Аргументы:
            cls: класс действия, для которого нужна фабрика.

        Возвращает:
            DependencyFactory — stateless-фабрика для резолва зависимостей.

        Исключения:
            TypeError: если cls не является классом.
            ValueError: если MetadataBuilder обнаруживает структурные ошибки.
        """
        class_id = id(cls)

        if class_id not in self._factory_cache:
            metadata = self.get(cls)

            gate = DependencyGate()
            for dep_info in metadata.dependencies:
                gate.register(dep_info)
            gate.freeze()

            self._factory_cache[class_id] = DependencyFactory(gate)

        return self._factory_cache[class_id]

    # ─────────────────────────────────────────────────────────────────────
    # Проверки и инвалидация
    # ─────────────────────────────────────────────────────────────────────

    def has(self, cls: type) -> bool:
        """
        Проверяет, есть ли метаданные класса в кеше.

        НЕ вызывает сборку — только проверяет наличие.
        """
        return id(cls) in self._cache

    def invalidate(self, cls: type) -> bool:
        """
        Удаляет метаданные и фабрику класса из кешей.

        Следующий вызов get(cls) пересоберёт метаданные заново,
        следующий вызов get_factory(cls) пересоздаст фабрику.
        Используется в тестах для сброса состояния координатора.

        Возвращает:
            True если метаданные были в кеше и удалены.
            False если метаданных не было.
        """
        class_id = id(cls)
        if class_id in self._cache:
            del self._cache[class_id]
            self._factory_cache.pop(class_id, None)
            del self._class_map[class_id]
            return True
        return False

    def invalidate_all(self) -> int:
        """
        Полностью очищает все кеши (метаданные, фабрики, карту классов).

        Возвращает:
            int — количество удалённых записей.
        """
        count = len(self._cache)
        self._cache.clear()
        self._factory_cache.clear()
        self._class_map.clear()
        return count

    # ─────────────────────────────────────────────────────────────────────
    # Инспекция
    # ─────────────────────────────────────────────────────────────────────

    def get_all_metadata(self) -> list[ClassMetadata]:
        """Возвращает список всех закешированных ClassMetadata."""
        return list(self._cache.values())

    def get_all_classes(self) -> list[type]:
        """Возвращает список всех зарегистрированных классов."""
        return list(self._class_map.values())

    @property
    def size(self) -> int:
        """Количество закешированных классов."""
        return len(self._cache)

    # ─────────────────────────────────────────────────────────────────────
    # Удобные методы (делегирование к ClassMetadata)
    # ─────────────────────────────────────────────────────────────────────

    def get_dependencies(self, cls: type) -> tuple[Any, ...]:
        """
        Возвращает кортеж зависимостей класса.

        Сокращение для coordinator.get(cls).dependencies.
        """
        return self.get(cls).dependencies

    def get_connections(self, cls: type) -> tuple[Any, ...]:
        """
        Возвращает кортеж соединений класса.

        Сокращение для coordinator.get(cls).connections.
        """
        return self.get(cls).connections

    def get_role(self, cls: type) -> RoleMeta | None:
        """
        Возвращает RoleMeta класса или None.

        Сокращение для coordinator.get(cls).role.
        """
        return self.get(cls).role

    def get_aspects(self, cls: type) -> tuple[Any, ...]:
        """
        Возвращает кортеж аспектов класса.

        Сокращение для coordinator.get(cls).aspects.
        """
        return self.get(cls).aspects

    def get_subscriptions(self, cls: type) -> tuple[Any, ...]:
        """
        Возвращает кортеж подписок класса (для плагинов).

        Сокращение для coordinator.get(cls).subscriptions.
        """
        return self.get(cls).subscriptions

    # ─────────────────────────────────────────────────────────────────────
    # Строковое представление
    # ─────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        """Компактное строковое представление координатора для отладки."""
        if not self._cache:
            return "GateCoordinator(empty)"

        class_names = ", ".join(
            meta.class_name for meta in self._cache.values()
        )
        return f"GateCoordinator(size={self.size}, classes=[{class_names}])"
