# src/action_machine/Checkers/checker_gate.py
"""
CheckerGate – шлюз для управления чекерами полей (валидаторами).

Хранит информацию о чекерах, прикреплённых к классам (валидация входных параметров)
и к методам (валидация результатов). На одно поле может быть несколько чекеров,
порядок регистрации сохраняется и важен для последовательной валидации.

После завершения сборки (в __init_subclass__ действия) шлюз замораживается,
и любые попытки регистрации или удаления вызывают RuntimeError.
"""

from collections.abc import Callable
from typing import Any

from action_machine.Checkers.BaseFieldChecker import BaseFieldChecker
from action_machine.Core.base_gate import BaseGate


class CheckerGate(BaseGate[BaseFieldChecker]):
    """
    Шлюз для управления чекерами полей.

    Внутреннее хранение:
        _class_checkers_order: list[BaseFieldChecker] – список классовых чекеров
                               в порядке регистрации.
        _class_checkers_by_field: dict[str, list[BaseFieldChecker]] – индекс для
                                   быстрого доступа к чекерам класса по имени поля.
        _method_checkers_order: list[tuple[Callable[..., Any], str, BaseFieldChecker]] –
                                список методных чекеров в порядке регистрации
                                (метод, имя поля, чекер).
        _method_checkers_by_method: dict[Callable[..., Any], dict[str, list[BaseFieldChecker]]] –
                                    индекс: метод → {имя поля → список чекеров}.
        _frozen: bool – флаг заморозки.
    """

    def __init__(self) -> None:
        """Инициализирует пустой шлюз чекеров."""
        self._class_checkers_order: list[BaseFieldChecker] = []
        self._class_checkers_by_field: dict[str, list[BaseFieldChecker]] = {}
        self._method_checkers_order: list[tuple[Callable[..., Any], str, BaseFieldChecker]] = []
        self._method_checkers_by_method: dict[Callable[..., Any], dict[str, list[BaseFieldChecker]]] = {}
        self._frozen: bool = False

    def _check_frozen(self) -> None:
        """Проверяет, не заморожен ли шлюз. Если заморожен – выбрасывает RuntimeError."""
        if self._frozen:
            raise RuntimeError("CheckerGate is frozen, cannot modify")

    def register(self, _component: BaseFieldChecker, **metadata: Any) -> BaseFieldChecker:
        """
        Регистрирует чекер.

        Метаданные должны содержать ключ 'target_type' со значением 'class' или 'method'.
        Для метода также требуется ключ 'method'.

        Несколько чекеров для одного поля разрешены; порядок регистрации сохраняется.

        Аргументы:
            _component: экземпляр чекера.
            **metadata: обязательные метаданные:
                - target_type: 'class' или 'method'.
                - method (только для метода): вызываемый объект метода.

        Возвращает:
            Зарегистрированный чекер.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
            ValueError: если отсутствуют обязательные метаданные или указан неверный тип.
        """
        self._check_frozen()

        target_type = metadata.get("target_type")
        if target_type not in ("class", "method"):
            raise ValueError("metadata['target_type'] must be 'class' or 'method'")

        if target_type == "class":
            field = _component.field_name
            # Добавляем в порядковый список
            self._class_checkers_order.append(_component)
            # Добавляем в индекс по полю
            self._class_checkers_by_field.setdefault(field, []).append(_component)

        else:  # target_type == "method"
            method = metadata.get("method")
            if method is None:
                raise ValueError("metadata['method'] is required for method checkers")
            field = _component.field_name

            # Добавляем в порядковый список
            self._method_checkers_order.append((method, field, _component))
            # Добавляем в индекс: метод → поле → список чекеров
            self._method_checkers_by_method.setdefault(method, {}).setdefault(field, []).append(_component)

        return _component

    def unregister(self, _component: BaseFieldChecker) -> None:
        """
        Удаляет чекер.

        Поскольку после заморозки изменения запрещены, метод выбрасывает исключение,
        если шлюз уже заморожен. В противном случае удаляет чекер из всех структур.

        Аргументы:
            _component: чекер для удаления.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
        """
        self._check_frozen()
        # Реализация удаления не требуется для production, так как шлюз замораживается.
        # Оставлен заглушкой для полноты интерфейса.
        pass

    def get_components(self) -> list[BaseFieldChecker]:
        """
        Возвращает список всех зарегистрированных чекеров в порядке регистрации
        (сначала классовые, затем методные).

        Возвращаемый список является копией.

        Возвращает:
            Список экземпляров чекеров.
        """
        result = self._class_checkers_order.copy()
        result.extend(c for (_, _, c) in self._method_checkers_order)
        return result

    # -------------------- Дополнительные методы для удобства --------------------

    def get_class_checkers(self, field_name: str | None = None) -> list[BaseFieldChecker]:
        """
        Возвращает список классовых чекеров.

        Аргументы:
            field_name: если указан, возвращает чекеры только для этого поля.

        Возвращает:
            Список чекеров (копия). Если field_name не найден, возвращает пустой список.
        """
        if field_name is not None:
            return self._class_checkers_by_field.get(field_name, []).copy()
        return self._class_checkers_order.copy()

    def get_method_checkers(
        self,
        method: Callable[..., Any],
        field_name: str | None = None
    ) -> list[BaseFieldChecker]:
        """
        Возвращает список методных чекеров для указанного метода.

        Аргументы:
            method: метод, для которого нужны чекеры.
            field_name: если указан, возвращает чекеры только для этого поля.

        Возвращает:
            Список чекеров (копия). Если method или field_name не найдены,
            возвращает пустой список.
        """
        method_index = self._method_checkers_by_method.get(method)
        if method_index is None:
            return []
        if field_name is not None:
            return method_index.get(field_name, []).copy()
        # Возвращаем все чекеры для метода в порядке регистрации
        result = []
        for m, f, c in self._method_checkers_order:
            if m is method:
                result.append(c)
        return result

    def get_all_method_checkers(self) -> list[tuple[Callable[..., Any], str, BaseFieldChecker]]:
        """
        Возвращает список всех методных чекеров в порядке регистрации.

        Возвращаемый список является копией.

        Возвращает:
            Список кортежей (метод, имя поля, чекер).
        """
        return self._method_checkers_order.copy()

    def freeze(self) -> None:
        """
        Замораживает шлюз, запрещая дальнейшие изменения.

        Вызывается после завершения сбора чекеров в __init_subclass__.
        """
        self._frozen = True