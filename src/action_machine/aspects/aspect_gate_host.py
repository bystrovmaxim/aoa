# src/action_machine/aspects/aspect_gate_host.py
"""
Хост для шлюза аспектов.

Класс-хост, который присоединяет шлюз аспектов к действию.
Собирает аспекты, помеченные декораторами regular_aspect и summary_aspect,
при создании подкласса и предоставляет к ним доступ через метод get_aspects().

ВАЖНО: Аспекты определяются один раз на уровне класса и не могут быть изменены
после создания класса. Нет публичного доступа к самому шлюзу — только к
неизменяемым кортежам (список обычных аспектов, summary-аспект).
Это обеспечивает полную инкапсуляцию и предотвращает случайные изменения.

Кэширование данных аспектов выполняется внутри класса при его создании,
чтобы не полагаться на внешний кэш (например, в ActionProductMachine).

Аспекты не наследуются. Каждый класс определяет свои аспекты независимо.
"""

from typing import Any

from .aspect_gate import AspectGate
from .aspect_method_protocol import AspectMethodProtocol


class AspectGateHost:
    """
    Класс-хост, который присоединяет шлюз аспектов к действию.

    Предоставляет:
        - Метод `get_aspects()` для машины (возвращает обычные и summary‑аспекты).
        - Автоматический сбор аспектов, помеченных декораторами
          (`@regular_aspect`, `@summary_aspect`), во время создания класса.
        - Проверку: если есть regular-аспекты, то должен быть summary-аспект.

    Особенности:
        - Нет публичного свойства `aspects` — доступ к шлюзу извне невозможен.
        - Нет методов для изменения аспектов на уровне экземпляра.
        - Все аспекты хранятся в приватных классовых атрибутах:
          `__regular_aspects` (список) и `__summary_aspect` (кортеж или None).
        - При наследовании каждый класс имеет свой собственный набор аспектов
          (аспекты не наследуются).

    Пример:
        class MyAction(AspectGateHost):
            @regular_aspect("Валидация")
            async def validate(...): ...

            @summary_aspect("Создание")
            async def create(...): ...
    """

    # Приватные классовые атрибуты для хранения закешированных данных
    __regular_aspects: list[tuple[AspectMethodProtocol, str]] | None = None
    __summary_aspect: tuple[AspectMethodProtocol, str] | None = None

    def __init__(self) -> None:
        """
        Инициализирует экземпляр.
        Проверяет, что если есть regular-аспекты, то есть summary.
        """
        regular = self.__class__.__regular_aspects
        summary = self.__class__.__summary_aspect
        if regular and summary is None:
            raise TypeError(
                f"Class {self.__class__.__name__} does not have a summary aspect. "
                "Each action must define exactly one summary aspect (use @summary_aspect)."
            )

    def get_aspects(self) -> tuple[list[tuple[AspectMethodProtocol, str]],
                                   tuple[AspectMethodProtocol, str] | None]:
        """
        Возвращает аспекты для выполнения.

        Используется машиной (ActionProductMachine) для получения списков
        обычных и summary-аспектов.

        Возвращаемые значения:
            - Список кортежей (метод, описание) для обычных аспектов.
            - Кортеж (метод, описание) для summary-аспекта, или None.

        Данные возвращаются из кэша, который заполняется один раз при создании класса.
        """
        regular = self.__class__.__regular_aspects
        summary = self.__class__.__summary_aspect
        # regular никогда не должен быть None после инициализации класса,
        # но на всякий случай возвращаем пустой список
        return regular or [], summary

    # ------------------------------------------------------------------
    # Сбор аспектов при создании класса
    # ------------------------------------------------------------------
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Вызывается автоматически при создании подкласса."""
        super().__init_subclass__(**kwargs)

        # Временные списки для сбора аспектов этого класса
        _class_regular = []
        _class_summary = None

        # Собираем методы с временным атрибутом _new_aspect_meta,
        # которые были добавлены декораторами regular_aspect и summary_aspect.
        methods_to_process = []
        for name, method in cls.__dict__.items():
            if hasattr(method, '_new_aspect_meta'):
                methods_to_process.append((name, method))

        for name, method in methods_to_process:
            meta = method._new_aspect_meta
            if meta['type'] == 'regular':
                _class_regular.append((method, meta['description']))
            elif meta['type'] == 'summary':
                if _class_summary is not None:
                    raise TypeError("Only one summary aspect can be registered per action.")
                _class_summary = (method, meta['description'])
            # Удаляем временные метаданные, чтобы не засорять метод
            delattr(method, '_new_aspect_meta')

        # Создаём шлюз для валидации и порядка (но не сохраняем его, только используем для извлечения)
        gate = AspectGate()
        for method, desc in _class_regular:
            gate.register(method, description=desc, type="regular")
        if _class_summary is not None:
            method, desc = _class_summary
            gate.register(method, description=desc, type="summary")

        # Сохраняем закешированные данные в приватные атрибуты класса
        # pylint: disable=unused-private-member
        cls.__regular_aspects = gate.get_regular()   # список копий (уже копия)
        cls.__summary_aspect = gate.get_summary()    # кортеж или None
        # pylint: enable=unused-private-member