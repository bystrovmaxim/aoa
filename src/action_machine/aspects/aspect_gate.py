# src/action_machine/aspects/aspect_gate.py
"""
Шлюз для управления аспектами действия.

Этот класс используется только внутри пакета action_machine.
Публичные методы предназначены исключительно для внутреннего использования.
"""

from typing import Any

from .aspect_method_protocol import AspectMethodProtocol


class AspectGate:
    """
    Шлюз для управления аспектами действия.

    Хранит:
        - Обычные аспекты (regular) – список кортежей (метод, описание)
          в порядке регистрации.
        - Один summary-аспект – кортеж (метод, описание).

    Методы:
        register(component, **metadata) – зарегистрировать аспект.
        unregister(component) – удалить аспект.
        get_regular() – список обычных аспектов с описаниями.
        get_summary() – summary-аспект (или None).

    ВАЖНО: Этот класс предназначен только для внутреннего использования
    в пакете action_machine. Внешний код не должен создавать экземпляры
    или вызывать методы этого класса напрямую.
    """

    def __init__(self) -> None:
        self._regular: list[tuple[AspectMethodProtocol, str]] = []
        self._summary: tuple[AspectMethodProtocol, str] | None = None

    def register(self, _component: AspectMethodProtocol, **metadata: Any) -> AspectMethodProtocol:
        """
        Зарегистрировать аспект.

        Аргументы:
            _component: метод‑аспект.
            **metadata: метаданные – должны содержать ключи 'description' и 'type'.

        Возвращает:
            Зарегистрированный метод.

        Исключения:
            ValueError: если зарегистрирован второй summary-аспект.
            ValueError: если тип аспекта неизвестен.
            KeyError: если в metadata отсутствует 'description' или 'type'.
        """
        description = metadata.get("description")
        aspect_type = metadata.get("type", "regular")

        if description is None:
            raise ValueError("Missing required metadata key 'description'")
        if aspect_type not in ("regular", "summary"):
            raise ValueError(f"Неизвестный тип аспекта: {aspect_type}")

        if aspect_type == "regular":
            self._regular.append((_component, description))
        else:  # summary
            if self._summary is not None:
                raise ValueError("Разрешён только один summary-аспект.")
            self._summary = (_component, description)

        return _component

    def unregister(self, component: AspectMethodProtocol) -> None:
        """Удалить аспект из шлюза."""
        for i, (m, _) in enumerate(self._regular):
            if m is component:
                self._regular.pop(i)
                return
        if self._summary and self._summary[0] is component:
            self._summary = None

    def get_regular(self) -> list[tuple[AspectMethodProtocol, str]]:
        """Вернуть список (метод, описание) для обычных аспектов в порядке регистрации."""
        return self._regular.copy()

    def get_summary(self) -> tuple[AspectMethodProtocol, str] | None:
        """Вернуть кортеж (метод, описание) для summary-аспекта или None."""
        return self._summary