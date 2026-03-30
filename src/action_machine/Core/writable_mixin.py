# ActionMachine/Core/WritableMixin.py
"""
Миксин для реализации протокола WritableDataProtocol
на основе атрибутов объекта.

Предназначен для использования совместно с ReadableMixin
в классах, которым требуется изменяемое состояние:
    - BaseState   — состояние конвейера аспектов (замена сырого dict).
    - BaseResult  — результат выполнения действия.

Не используется в BaseParams (параметры действия — только для чтения)
и в Context-компонентах (UserInfo, RequestInfo, EnvironmentInfo —
frozen dataclass, неизменяемые после создания).

Обеспечивает dict-подобный интерфейс для записи и удаления:
    - obj['key'] = value  — запись через __setitem__.
    - del obj['key']      — удаление через __delitem__.
    - obj.write(key, value, allowed_keys) — контролируемая запись
      с валидацией по списку разрешённых ключей.

Метод write предоставляет дополнительный уровень контроля:
    - Проверяет, что ключ входит в список разрешённых (allowed_keys).
    - Если ключ не разрешён — выбрасывает KeyError с информативным сообщением.
    - Если allowed_keys не задан (None) — запись разрешена для любого ключа.

Это позволяет плагинам и аспектам ограничивать набор полей,
которые могут быть изменены на конкретном этапе конвейера,
предотвращая случайную перезапись критичных данных.

Пример:
    >>> from action_machine.Core.BaseState import BaseState
    >>> state = BaseState({"total": 1500})
    >>> state["discount"] = 100
    >>> state.write("final", 1400, allowed_keys=["final", "discount"])
    >>> del state["discount"]
    >>> state.to_dict()
    {'total': 1500, 'final': 1400}
"""

from typing import Any


class WritableMixin:
    """
    Реализует WritableDataProtocol через атрибуты объекта.

    Позволяет записывать и удалять атрибуты через dict-подобный интерфейс.
    Метод write добавляет опциональную валидацию по списку разрешённых ключей.

    Используется как базовый класс для BaseState и BaseResult.
    Не используется в BaseParams (только чтение) и Context-компонентах
    (frozen dataclass).
    """

    # ---------- Базовая запись и удаление ----------

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Запись значения по ключу через setattr.

        Аргументы:
            key:   имя атрибута (строка).
            value: значение для записи (любой тип).

        Пример:
            >>> state = BaseState()
            >>> state["count"] = 42
            >>> state.count
            42
        """
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        """
        Удаление атрибута по ключу через delattr.

        Аргументы:
            key: имя атрибута (строка).

        Исключения:
            KeyError: если атрибут не существует.

        Пример:
            >>> state = BaseState({"temp": True})
            >>> del state["temp"]
            >>> "temp" in state
            False
        """
        try:
            delattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    # ---------- Контролируемая запись ----------
    #
    # Метод write позволяет плагинам и аспектам ограничивать
    # набор полей, доступных для записи на конкретном этапе.
    #
    # Это предотвращает ситуации, когда плагин случайно
    # перезаписывает поле, установленное предыдущим аспектом.
    #
    # Если allowed_keys=None — валидация отключена,
    # запись разрешена для любого ключа (поведение по умолчанию).

    def write(
        self,
        key: str,
        value: Any,
        allowed_keys: list[str] | None = None,
    ) -> None:
        """
        Контролируемая запись значения по ключу.

        Если передан список allowed_keys, метод проверяет,
        что key входит в этот список. Если ключ не разрешён —
        выбрасывает KeyError с информативным сообщением.

        Если allowed_keys=None — запись разрешена для любого ключа
        (эквивалентно obj[key] = value).

        Аргументы:
            key:          имя атрибута для записи (строка).
            value:        значение для записи (любой тип).
            allowed_keys: список разрешённых ключей, или None
                          если валидация не требуется.

        Исключения:
            KeyError: если key не входит в allowed_keys
                      (при allowed_keys is not None).

        Пример:
            # ТЕСТЫ: Передача параметров в write
            >>> state = BaseState()
            >>> state.write("total", 1500, allowed_keys=["total", "discount"])
            >>> state.total
            1500

            # ТЕСТЫ: Разрешённые операции
            >>> state.write("discount", 100, allowed_keys=["total", "discount"])
            >>> state.discount
            100

            >>> state.write("secret", 42, allowed_keys=["total", "discount"])
            KeyError: "Ключ 'secret' не входит в список разрешённых: ['total', 'discount']"
        """
        if allowed_keys is not None and key not in allowed_keys:
            raise KeyError(
                f"Ключ '{key}' не входит в список разрешённых: {allowed_keys}"
            )
        setattr(self, key, value)

    # ---------- Массовое обновление ----------
    #
    # Метод update позволяет записать несколько пар ключ-значение
    # за один вызов. Удобен для инициализации состояния
    # из словаря или для применения пакета изменений от плагина.

    def update(self, data: dict[str, Any]) -> None:
        """
        Массовое обновление атрибутов из словаря.

        Каждая пара (key, value) из data записывается через setattr.
        Существующие атрибуты перезаписываются, новые — создаются.

        Аргументы:
            data: словарь с парами (ключ, значение) для записи.

        Пример:
            # ТЕСТЫ: Простые реализации
            >>> state = BaseState()
            >>> state.update({"a": 1, "b": 2})
            >>> state.a, state.b
            (1, 2)
        """
        for key, value in data.items():
            setattr(self, key, value)
