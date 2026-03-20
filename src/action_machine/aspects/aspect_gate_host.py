# src/action_machine/aspects/aspect_gate_host.py
"""
Хост для шлюза аспектов.

Класс-хост, который присоединяет шлюз аспектов к действию.
Собирает аспекты, помеченные декораторами regular_aspect и summary_aspect,
при создании подкласса и предоставляет к ним доступ через свойство aspects.

ВАЖНО: Аспекты не наследуются. Каждый класс определяет свои аспекты независимо.
"""

from typing import Any, cast

from .aspect_gate import AspectGate
from .aspect_method_protocol import AspectMethodProtocol


class AspectGateHost:
    """
    Класс-хост, который присоединяет шлюз аспектов к действию.

    Предоставляет:
        - Ленивое создание экземплярного шлюза аспектов (свойство `aspects`).
        - Метод `get_aspects()` для машины (возвращает обычные и summary‑аспекты).
        - Автоматический сбор аспектов, помеченных декораторами
          (`@regular_aspect`, `@summary_aspect`), во время создания класса.
        - Проверку: если есть regular-аспекты, то должен быть summary-аспект.

    Примечание:
        Аспекты не наследуются от родительских классов. Каждый класс определяет
        свои аспекты независимо.

    Пример:
        class MyAction(AspectGateHost):
            @regular_aspect("Валидация")
            async def validate(...): ...

            @summary_aspect("Создание")
            async def create(...): ...
    """

    # Классовый шлюз (общий для всех экземпляров) – создаётся один раз при определении класса
    _class_gate: AspectGate | None = None

    def __init__(self) -> None:
        """
        Инициализирует экземпляр.
        Проверяет, что если есть regular-аспекты, то есть summary.
        """
        class_gate = self.__class__._class_gate
        if class_gate is None:
            # Это не должно случиться, так как __init_subclass__ создаёт _class_gate,
            # но защита на случай, если класс определён без аспектов.
            self.__class__._class_gate = AspectGate()
            class_gate = self.__class__._class_gate
        regular, summary = class_gate.get_regular(), class_gate.get_summary()
        if regular and summary is None:
            raise TypeError(
                f"Class {self.__class__.__name__} does not have a summary aspect. "
                "Each action must define exactly one summary aspect (use @summary_aspect)."
            )
        # Экземплярный шлюз – изначально None (используем классовый)
        self._instance_gate: AspectGate | None = None

    @property
    def aspects(self) -> AspectGate:
        """
        Возвращает шлюз аспектов для данного экземпляра.

        Если у экземпляра ещё нет собственного шлюза, возвращается классовый (общий).
        """
        if self._instance_gate is not None:
            return self._instance_gate
        # Классовый шлюз всегда существует
        return cast(AspectGate, self.__class__._class_gate)

    def get_aspects(self) -> tuple[list[tuple[AspectMethodProtocol, str]],
                                   tuple[AspectMethodProtocol, str] | None]:
        """
        Возвращает аспекты для выполнения.

        Используется машиной (ActionProductMachine) для получения списков
        обычных и summary-аспектов.

        Возвращает:
            Кортеж (regular_aspects, summary_aspect). Обычные аспекты – список
            кортежей (метод, описание). Summary-аспект – кортеж (метод, описание)
            или None.
        """
        gate = self.aspects
        return gate.get_regular(), gate.get_summary()

    # ------------------------------------------------------------------
    # Методы для изменения аспектов (copy-on-write)
    # ------------------------------------------------------------------
    def _ensure_copy(self) -> None:
        """Создаёт копию классового шлюза, если у экземпляра ещё нет своего."""
        if self._instance_gate is None:
            class_gate = self.__class__._class_gate
            # class_gate не может быть None, потому что __init_subclass__ создаёт его
            assert class_gate is not None
            new_gate = AspectGate()
            # Копируем обычные аспекты
            for method, desc in class_gate.get_regular():
                new_gate.register(method, description=desc, type="regular")
            # Копируем summary
            summary = class_gate.get_summary()
            if summary is not None:
                method, desc = summary
                new_gate.register(method, description=desc, type="summary")
            self._instance_gate = new_gate

    def add_regular_aspect(self, method: AspectMethodProtocol, description: str) -> None:
        """
        Добавляет обычный аспект к текущему экземпляру действия.
        При первом добавлении создаётся локальная копия классового шлюза.
        """
        self._ensure_copy()
        # После вызова _ensure_copy self._instance_gate точно не None
        assert self._instance_gate is not None
        self._instance_gate.register(method, description=description, type="regular")

    def remove_regular_aspect(self, method: AspectMethodProtocol) -> None:
        """Удаляет обычный аспект из текущего экземпляра."""
        self._ensure_copy()
        assert self._instance_gate is not None
        self._instance_gate.unregister(method)

    def set_summary_aspect(self, method: AspectMethodProtocol, description: str) -> None:
        """
        Устанавливает summary-аспект для текущего экземпляра.
        Если summary уже был, он заменяется.
        """
        self._ensure_copy()
        assert self._instance_gate is not None
        # Удаляем существующий summary, если есть
        current = self._instance_gate.get_summary()
        if current is not None:
            self._instance_gate.unregister(current[0])
        self._instance_gate.register(method, description=description, type="summary")

    def remove_summary_aspect(self) -> None:
        """Удаляет summary-аспект из текущего экземпляра."""
        self._ensure_copy()
        assert self._instance_gate is not None
        current = self._instance_gate.get_summary()
        if current is not None:
            self._instance_gate.unregister(current[0])

    # ------------------------------------------------------------------
    # Сбор аспектов при создании класса
    # ------------------------------------------------------------------
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Вызывается автоматически при создании подкласса."""
        super().__init_subclass__(**kwargs)

        # Инициализируем собственные списки аспектов для класса (пустые)
        # Используем обычные переменные без аннотаций, чтобы mypy не ругался
        cls._class_regular = []  # type: ignore[attr-defined]
        cls._class_summary = None  # type: ignore[attr-defined]

        # Собираем методы с временным атрибутом _new_aspect_meta
        methods_to_process = []
        for name, method in cls.__dict__.items():
            if hasattr(method, '_new_aspect_meta'):
                methods_to_process.append((name, method))

        for name, method in methods_to_process:
            meta = method._new_aspect_meta
            if meta['type'] == 'regular':
                cls._class_regular.append((method, meta['description']))  # type: ignore[attr-defined]
            elif meta['type'] == 'summary':
                # Проверка на дублирование summary-аспекта
                if cls._class_summary is not None:  # type: ignore[attr-defined]
                    raise TypeError("Only one summary aspect can be registered per action.")
                cls._class_summary = (method, meta['description'])  # type: ignore[attr-defined]
            # Удаляем временные метаданные
            delattr(method, '_new_aspect_meta')

        # Создаём классовый шлюз и регистрируем в нём собранные аспекты
        gate = AspectGate()
        for method, desc in cls._class_regular:  # type: ignore[attr-defined]
            gate.register(method, description=desc, type="regular")
        if cls._class_summary is not None:  # type: ignore[attr-defined]
            method, desc = cls._class_summary  # type: ignore[attr-defined]
            gate.register(method, description=desc, type="summary")
        cls._class_gate = gate

        # Очищаем временные списки (они больше не нужны)
        delattr(cls, '_class_regular')
        delattr(cls, '_class_summary')