# src/action_machine/aspects/aspect_gate_host.py

from typing import Optional, Tuple, List
from .aspect_gate import AspectGate
from .aspect_method_protocol import AspectMethodProtocol as AspectMethodProtocol


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

    # Классовые хранилища аспектов (только для текущего класса)
    _class_regular: List[Tuple[AspectMethodProtocol, str]] = []
    _class_summary: Optional[Tuple[AspectMethodProtocol, str]] = None

    def __init__(self) -> None:
        """
        Инициализирует экземпляр.
        Проверяет, что если есть regular-аспекты, то есть summary.
        """
        if self.__class__._class_regular and self.__class__._class_summary is None:
            raise TypeError(
                f"Class {self.__class__.__name__} does not have a summary aspect. "
                "Each action must define exactly one summary aspect (use @summary_aspect)."
            )
        # Экземплярный шлюз создаётся лениво при первом обращении к свойству `aspects`
        self._aspects_gate: Optional[AspectGate] = None

    @property
    def aspects(self) -> AspectGate:
        """
        Лениво создаёт и возвращает экземплярный шлюз аспектов.
        Копирует в него классовые списки аспектов.
        """
        if self._aspects_gate is None:
            gate = AspectGate()
            # Копируем обычные аспекты из класса
            for method, desc in self.__class__._class_regular:
                gate.register(method, description=desc, type="regular")
            # Копируем summary-аспект из класса
            if self.__class__._class_summary:
                method, desc = self.__class__._class_summary
                gate.register(method, description=desc, type="summary")
            self._aspects_gate = gate
        return self._aspects_gate

    def get_aspects(self) -> Tuple[List[Tuple[AspectMethodProtocol, str]],
                                   Optional[Tuple[AspectMethodProtocol, str]]]:
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

    def __init_subclass__(cls, **kwargs):
        """Вызывается автоматически при создании подкласса."""
        super().__init_subclass__(**kwargs)

        # Регистрация аспектов ТОЛЬКО из текущего класса (без наследования)
        # Сначала собираем методы с мета-атрибутом в список, чтобы не менять __dict__ во время итерации
        methods_to_process = []
        for name, method in cls.__dict__.items():
            if hasattr(method, '_new_aspect_meta'):
                methods_to_process.append((name, method))

        for name, method in methods_to_process:
            meta = method._new_aspect_meta
            if meta['type'] == 'regular':
                cls._class_regular.append((method, meta['description']))
            elif meta['type'] == 'summary':
                # Проверка на дублирование summary-аспекта
                if cls._class_summary is not None:
                    raise TypeError("Only one summary aspect can be registered per action.")
                cls._class_summary = (method, meta['description'])
            # Удаляем временные метаданные
            delattr(method, '_new_aspect_meta')