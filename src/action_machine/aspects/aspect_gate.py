# src/action_machine/aspects/aspect_gate.py

from typing import List, Tuple, Optional
from action_machine.Core.base_gate import BaseGate
from .aspect_method_protocol import AspectMethodProtocol as AspectMethodProtocol


class AspectGate(BaseGate[AspectMethodProtocol]):
    """
    Шлюз для управления аспектами действия.

    Хранит:
        - Обычные аспекты (regular) – список кортежей (метод, описание)
          в порядке регистрации.
        - Один summary-аспект – кортеж (метод, описание).

    Методы:
        register(method, description, type) – зарегистрировать аспект.
        unregister(method) – удалить аспект.
        get_components() – список всех аспектов.
        get_regular() – список обычных аспектов с описаниями.
        get_summary() – summary-аспект (или None).
    """

    def __init__(self):
        self._regular: List[Tuple[AspectMethodProtocol, str]] = []
        self._summary: Optional[Tuple[AspectMethodProtocol, str]] = None

    def register(self, method: AspectMethodProtocol, description: str, type: str = "regular") -> AspectMethodProtocol:
        """
        Зарегистрировать аспект.

        Аргументы:
            method: метод‑аспект.
            description: описание (для логов и документации).
            type: тип – "regular" (по умолчанию) или "summary".

        Возвращает:
            Зарегистрированный метод.

        Исключения:
            ValueError: если зарегистрирован второй summary-аспект.
            ValueError: если тип неизвестен.
        """
        if type == "regular":
            self._regular.append((method, description))
        elif type == "summary":
            if self._summary is not None:
                raise ValueError("Разрешён только один summary-аспект.")
            self._summary = (method, description)
        else:
            raise ValueError(f"Неизвестный тип аспекта: {type}")
        return method

    def unregister(self, method: AspectMethodProtocol) -> None:
        """Удалить аспект из шлюза."""
        for i, (m, _) in enumerate(self._regular):
            if m is method:
                self._regular.pop(i)
                return
        if self._summary and self._summary[0] is method:
            self._summary = None

    def get_components(self) -> List[AspectMethodProtocol]:
        """Вернуть все зарегистрированные аспекты (сначала обычные, потом summary)."""
        result = [m for m, _ in self._regular]
        if self._summary:
            result.append(self._summary[0])
        return result

    def get_regular(self) -> List[Tuple[AspectMethodProtocol, str]]:
        """Вернуть список (метод, описание) для обычных аспектов в порядке регистрации."""
        return self._regular.copy()

    def get_summary(self) -> Optional[Tuple[AspectMethodProtocol, str]]:
        """Вернуть кортеж (метод, описание) для summary-аспекта или None."""
        return self._summary