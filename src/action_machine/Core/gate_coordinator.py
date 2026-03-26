# src/action_machine/Core/gate_coordinator.py
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
   Благодаря этому при добавлении нового типа декоратора координатор НЕ
   меняется — меняется только MetadataBuilder.

2. ПОТОКОБЕЗОПАСНОСТЬ: GateCoordinator не использует блокировки, потому что
   в asyncio-среде код выполняется в одном потоке. Если потребуется
   многопоточность — достаточно добавить threading.Lock вокруг _cache.

3. ОТКРЫТ ДЛЯ РАСШИРЕНИЯ, ЗАКРЫТ ДЛЯ МОДИФИКАЦИИ (OCP): новый декоратор
   → новое поле в ClassMetadata → новый _collect_* в MetadataBuilder.
   GateCoordinator не затрагивается.

4. СИНГЛТОН ИЛИ ИНЪЕКЦИЯ: координатор можно использовать как синглтон
   (модульный экземпляр) или передавать через DI. Оба варианта поддерживаются.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.Core.gate_coordinator import GateCoordinator

    # Вариант 1: создание экземпляра
    coordinator = GateCoordinator()

    # Получение метаданных (ленивая сборка при первом вызове):
    meta = coordinator.get(CreateOrderAction)
    print(meta.role.spec)          # "user"
    print(meta.dependencies)       # (DependencyInfo(...), ...)
    print(meta.get_summary_aspect())  # AspectMeta(...)

    # Повторный вызов — из кеша, мгновенно:
    meta2 = coordinator.get(CreateOrderAction)
    assert meta is meta2  # тот же объект

    # Инвалидация (для тестов):
    coordinator.invalidate(CreateOrderAction)

    # Вариант 2: использование модульного синглтона:
    from action_machine.Core.gate_coordinator import default_coordinator
    meta = default_coordinator.get(CreateOrderAction)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from action_machine.Core.metadata_builder import MetadataBuilder

if TYPE_CHECKING:
    from action_machine.Core.class_metadata import ClassMetadata


class GateCoordinator:
    """
    Центральный реестр и кеш ClassMetadata.

    Хранит собранные метаданные классов и предоставляет к ним доступ.
    При первом обращении к классу автоматически вызывает MetadataBuilder.build()
    и кеширует результат. Повторные обращения возвращают кешированный объект.

    Атрибуты:
        _cache : dict[int, ClassMetadata]
            Кеш метаданных. Ключ — id(cls), значение — ClassMetadata.
            Использование id(cls) вместо самого cls в качестве ключа
            предотвращает проблемы с классами, переопределяющими __hash__.

        _class_map : dict[int, type]
            Обратная карта id(cls) → cls. Нужна для методов инспекции
            (get_all_classes, __repr__), где требуется восстановить
            класс по его id.
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
        и кеширует результат. Все последующие вызовы возвращают
        кешированный объект.

        Аргументы:
            cls: класс, метаданные которого нужно получить.

        Возвращает:
            ClassMetadata — иммутабельный снимок метаданных класса.

        Исключения:
            TypeError: если cls не является классом.
            ValueError: если MetadataBuilder обнаруживает структурные ошибки
                        (например, два summary-аспекта).

        Пример:
            >>> coordinator = GateCoordinator()
            >>> meta = coordinator.get(CreateOrderAction)
            >>> meta.class_name
            'test_full_flow.CreateOrderAction'
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
        «зарегистрировать класс заранее», а не «получить метаданные
        по необходимости». Используется при старте приложения для
        предварительной сборки метаданных всех Action-классов.

        Аргументы:
            cls: класс для регистрации.

        Возвращает:
            ClassMetadata — собранные метаданные.

        Пример:
            >>> coordinator = GateCoordinator()
            >>> coordinator.register(CreateOrderAction)
            >>> coordinator.register(PingAction)
            >>> # Все метаданные уже в кеше, get() будет мгновенным.
        """
        return self.get(cls)

    def has(self, cls: type) -> bool:
        """
        Проверяет, есть ли метаданные класса в кеше.

        НЕ вызывает сборку — только проверяет наличие.

        Аргументы:
            cls: класс для проверки.

        Возвращает:
            True если метаданные уже собраны и закешированы.
        """
        return id(cls) in self._cache

    def invalidate(self, cls: type) -> bool:
        """
        Удаляет метаданные класса из кеша.

        Следующий вызов get(cls) пересоберёт метаданные заново.
        Используется в тестах или при динамическом переопределении
        декораторов.

        Аргументы:
            cls: класс, кеш которого нужно сбросить.

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

        Возвращает количество удалённых записей. Используется в тестах
        для гарантии чистого состояния между тестовыми сценариями.

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
        """
        Возвращает список всех закешированных ClassMetadata.

        Порядок не гарантирован. Используется для отладки,
        генерации документации или инспекции зарегистрированных классов.

        Возвращает:
            list[ClassMetadata] — все метаданные из кеша.
        """
        return list(self._cache.values())

    def get_all_classes(self) -> list[type]:
        """
        Возвращает список всех зарегистрированных классов.

        Возвращает:
            list[type] — классы, для которых есть метаданные в кеше.
        """
        return list(self._class_map.values())

    @property
    def size(self) -> int:
        """
        Количество закешированных классов.

        Возвращает:
            int — размер кеша.
        """
        return len(self._cache)

    # ─────────────────────────────────────────────────────────────────────
    # Удобные методы (делегирование к ClassMetadata)
    # ─────────────────────────────────────────────────────────────────────

    def get_dependencies(self, cls: type) -> tuple:
        """
        Возвращает кортеж зависимостей класса.

        Сокращение для coordinator.get(cls).dependencies.

        Аргументы:
            cls: класс.

        Возвращает:
            tuple[DependencyInfo, ...] — зависимости.
        """
        return self.get(cls).dependencies

    def get_connections(self, cls: type) -> tuple:
        """
        Возвращает кортеж соединений класса.

        Сокращение для coordinator.get(cls).connections.

        Аргументы:
            cls: класс.

        Возвращает:
            tuple[ConnectionInfo, ...] — соединения.
        """
        return self.get(cls).connections

    def get_role(self, cls: type):
        """
        Возвращает RoleMeta класса или None.

        Сокращение для coordinator.get(cls).role.

        Аргументы:
            cls: класс.

        Возвращает:
            RoleMeta | None — ролевые метаданные.
        """
        return self.get(cls).role

    def get_aspects(self, cls: type) -> tuple:
        """
        Возвращает кортеж аспектов класса.

        Сокращение для coordinator.get(cls).aspects.

        Аргументы:
            cls: класс.

        Возвращает:
            tuple[AspectMeta, ...] — аспекты.
        """
        return self.get(cls).aspects

    def get_subscriptions(self, cls: type) -> tuple:
        """
        Возвращает кортеж подписок класса (для плагинов).

        Сокращение для coordinator.get(cls).subscriptions.

        Аргументы:
            cls: класс.

        Возвращает:
            tuple[SubscriptionInfo, ...] — подписки.
        """
        return self.get(cls).subscriptions

    # ─────────────────────────────────────────────────────────────────────
    # Строковое представление
    # ─────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        """
        Компактное строковое представление координатора для отладки.

        Показывает количество закешированных классов и их имена.
        """
        if not self._cache:
            return "GateCoordinator(empty)"

        class_names = ", ".join(
            meta.class_name for meta in self._cache.values()
        )
        return f"GateCoordinator(size={self.size}, classes=[{class_names}])"


# ═════════════════════════════════════════════════════════════════════════════
# Модульный синглтон
# ═════════════════════════════════════════════════════════════════════════════

default_coordinator: GateCoordinator = GateCoordinator()
"""
Синглтон координатора на уровне модуля.

Может использоваться напрямую для простых сценариев:

    from action_machine.Core.gate_coordinator import default_coordinator
    meta = default_coordinator.get(CreateOrderAction)

Для тестов рекомендуется создавать отдельный экземпляр GateCoordinator(),
чтобы избежать загрязнения кеша между тестами.
"""
