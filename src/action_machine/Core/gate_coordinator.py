# src/action_machine/core/gate_coordinator.py
"""
Модуль: GateCoordinator — центральный реестр и кеш ClassMetadata.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

GateCoordinator — единственная точка доступа к метаданным классов во всей
системе ActionMachine. Он отвечает за:

1. ЛЕНИВУЮ СБОРКУ: при первом обращении к классу координатор вызывает
   MetadataBuilder.build(cls), получает ClassMetadata и кеширует его.
   Повторные обращения возвращают кешированный объект мгновенно.

2. КЕШИРОВАНИЕ: каждый класс собирается ровно один раз. Кеш привязан
   к id(cls), что гарантирует корректность при наличии одноимённых классов
   из разных модулей.

3. ЕДИНООБРАЗНЫЙ ДОСТУП: вместо разрозненных обращений к cls._depends_info,
   cls._role_info и т.д. — один вызов coordinator.get(cls) возвращает
   полный снимок.

4. ИНВАЛИДАЦИЯ (опционально): метод invalidate(cls) удаляет кеш для класса.
   Используется в тестах или при динамическом переопределении декораторов.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ┌───────────────────────┐
    │  ActionProductMachine  │
    │  PluginCoordinator     │        потребители
    │  AuthCoordinator       │
    └──────────┬────────────┘
               │
               │  coordinator.get(cls)
               ▼
    ┌───────────────────┐
    │  GateCoordinator   │
    │                   │
    │  _cache: dict     │──── id(cls) → ClassMetadata
    │                   │
    └──────────┬────────┘
               │  cache miss → MetadataBuilder.build(cls)
               ▼
    ┌──────────────────┐
    │  MetadataBuilder  │
    └──────────────────┘

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. КООРДИНАТОР НЕ ЗНАЕТ О БИЗНЕС-ЛОГИКЕ: он не проверяет роли, не резолвит
   зависимости, не запускает аспекты. Он только хранит и отдаёт метаданные.

2. ПОТОКОБЕЗОПАСНОСТЬ: GateCoordinator не использует блокировки, потому что
   в asyncio-среде код выполняется в одном потоке.

3. ОТКРЫТ ДЛЯ РАСШИРЕНИЯ, ЗАКРЫТ ДЛЯ МОДИФИКАЦИИ (OCP): новый декоратор
   → новое поле в ClassMetadata → новый _collect_* в MetadataBuilder.
   GateCoordinator не затрагивается.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

    coordinator = GateCoordinator()

    meta = coordinator.get(CreateOrderAction)
    print(meta.role.spec)
    print(meta.dependencies)

    # Повторный вызов — из кеша:
    meta2 = coordinator.get(CreateOrderAction)
    assert meta is meta2

    # Инвалидация (для тестов):
    coordinator.invalidate(CreateOrderAction)
"""

from __future__ import annotations

from typing import Any

from action_machine.core.class_metadata import ClassMetadata, RoleMeta
from action_machine.core.metadata_builder import MetadataBuilder


class GateCoordinator:
    """
    Центральный реестр и кеш ClassMetadata.

    Хранит собранные метаданные классов и предоставляет к ним доступ.
    При первом обращении к классу автоматически вызывает MetadataBuilder.build()
    и кеширует результат. Повторные обращения возвращают кешированный объект.

    Экземпляр GateCoordinator создаётся явно и передаётся в конструктор
    ActionProductMachine или ActionTestMachine через dependency injection.
    Глобальных синглтонов не существует — каждый экземпляр машины владеет
    своим координатором (или разделяет его с другими машинами осознанно).

    Атрибуты:
        _cache : dict[int, ClassMetadata]
            Кеш метаданных. Ключ — id(cls), значение — ClassMetadata.

        _class_map : dict[int, type]
            Обратная карта id(cls) → cls. Нужна для методов инспекции.
    """

    def __init__(self) -> None:
        """
        Создаёт пустой координатор.

        Кеш заполняется лениво — при первом вызове get().
        """
        self._cache: dict[int, ClassMetadata] = {}
        self._class_map: dict[int, type] = {}

    # ─────────────────────────────────────────────────────────────────────
    # Основной API
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

    def has(self, cls: type) -> bool:
        """
        Проверяет, есть ли метаданные класса в кеше.

        НЕ вызывает сборку — только проверяет наличие.
        """
        return id(cls) in self._cache

    def invalidate(self, cls: type) -> bool:
        """
        Удаляет метаданные класса из кеша.

        Следующий вызов get(cls) пересоберёт метаданные заново.
        Используется в тестах для сброса состояния координатора.

        Возвращает:
            True если метаданные были в кеше и удалены.
            False если метаданных не было.
        """
        class_id = id(cls)
        if class_id in self._cache:
            del self._cache[class_id]
            del self._class_map[class_id]
            return True
        return False

    def invalidate_all(self) -> int:
        """
        Полностью очищает кеш.

        Возвращает:
            int — количество удалённых записей.
        """
        count = len(self._cache)
        self._cache.clear()
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
