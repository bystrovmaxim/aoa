# src/action_machine/domain/base_schema.py
"""
BaseSchema — базовый класс для всех схем домена.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseSchema — абстрактный базовый класс для всех сущностей и схем домена.
Наследует Pydantic BaseModel с настройками, подходящими для домена:

- frozen=True: объекты иммутабельны после создания (нет случайных мутаций).
- extra="forbid": запрещает лишние поля (строгая схема).
- validate_assignment=True: валидация при присваивании (если frozen=False).

Предоставляет dict-подобный доступ через __getitem__/__setitem__,
dot-path навигацию через resolve(), сериализацию через model_dump().

═══════════════════════════════════════════════════════════════════════════════
ПОЧЕМУ НЕ НАСЛЕДОВАТЬ ОТ dict
═══════════════════════════════════════════════════════════════════════════════

Pydantic даёт:
- Автоматическую валидацию типов и constraints (Field(ge=0)).
- Сериализацию/десериализацию (model_dump(), model_validate()).
- Автодокументацию полей (Field(description)).
- IDE-подсказки и mypy-проверки.

Dict-подобный API добавлен через __getitem__/__setitem__ для совместимости
с существующим кодом ActionMachine, который использует state["key"].

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ДОСТУП
═══════════════════════════════════════════════════════════════════════════════

BaseSchema ведёт себя как dict для чтения/записи полей:

    entity = OrderEntity(id="ORD-001", amount=100.0)
    entity["id"]        # → "ORD-001"
    entity["amount"]    # → 100.0
    entity["id"] = "ORD-002"  # RuntimeError если frozen=True

Для вложенных объектов — рекурсивный доступ:

    order.customer["name"] = "John"  # если customer — AssociationOne[Customer]

═══════════════════════════════════════════════════════════════════════════════
DOT-PATH НАВИГАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Метод resolve() позволяет обращаться к вложенным полям через строку:

    order.resolve("customer.name")     # → имя клиента
    order.resolve("items.0.price")     # → цена первого товара

Поддерживает:
- Простые поля: "id"
- Вложенные объекты: "customer.name"
- Списки: "items.0.price", "items.*.price" (первый/все)
- Отсутствующие поля: KeyError с понятным сообщением

═══════════════════════════════════════════════════════════════════════════════
СЕРИАЛИЗАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

Через model_dump() из Pydantic:

    data = entity.model_dump()  # → {"id": "ORD-001", "amount": 100.0, ...}

Для внешнего API рекомендуется создавать отдельные DTO, а не использовать
model_dump() напрямую (могут быть контейнеры связей с внутренней структурой).

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ И ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

Pydantic-валидация при создании:

    OrderEntity(id="ORD-001", amount=-10)  # ValidationError: amount >= 0

При frozen=True — ValidationError при попытке мутации:

    entity.amount = -10  # ValidationError

═══════════════════════════════════════════════════════════════════════════════
ПОЧЕМУ ABC
═══════════════════════════════════════════════════════════════════════════════

BaseSchema — абстрактный класс. Нельзя создать экземпляр BaseSchema() напрямую.
Это предотвращает использование как общего контейнера данных.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel, ABC):
    """
    Базовый класс для всех схем домена.

    Иммутабельный (frozen=True), строгая схема (extra="forbid"),
    dict-подобный доступ, dot-path навигация.
    """

    model_config = ConfigDict(
        frozen=True,          # Иммутабельность
        extra="forbid",       # Запрет лишних полей
        validate_assignment=True,  # Валидация при присваивании
    )

    def __getitem__(self, key: str) -> Any:
        """
        Dict-подобный доступ для чтения поля.

        entity["id"] эквивалентно entity.id

        Аргументы:
            key: имя поля.

        Возвращает:
            Значение поля.

        Исключения:
            KeyError: если поле не существует.
        """
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(f"Поле '{key}' не найдено в {self.__class__.__name__}") from e

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Dict-подобный доступ для записи поля.

        entity["id"] = "new" эквивалентно entity.id = "new"

        Аргументы:
            key: имя поля.
            value: новое значение.

        Исключения:
            ValidationError: если значение не проходит валидацию.
            RuntimeError: если frozen=True (иммутабельность).
        """
        setattr(self, key, value)

    def resolve(self, path: str) -> Any:
        """
        Разрешает dot-path к вложенному полю.

        Поддерживает:
        - Простые поля: "id"
        - Вложенные объекты: "customer.name"
        - Списки: "items.0.price" (первый элемент), "items.*.price" (все цены)

        Аргументы:
            path: dot-path к полю.

        Возвращает:
            Значение поля.

        Исключения:
            KeyError: если путь не существует или поле не загружено.
            ValueError: если путь malformed.
        """
        if not path:
            raise ValueError("Путь не может быть пустым")

        parts = path.split(".")
        current: Any = self

        for i, part in enumerate(parts):
            if part == "*":
                # items.*.price — рекурсивно для всех элементов списка
                if not isinstance(current, list):
                    raise KeyError(f"Ожидался список на пути '{'.'.join(parts[:i])}', получен {type(current)}")
                if i == len(parts) - 1:
                    raise ValueError("'*' не может быть последним элементом пути")
                # Рекурсивно разрешаем для каждого элемента
                sub_path = ".".join(parts[i+1:])
                return [item.resolve(sub_path) if hasattr(item, "resolve") else getattr(item, sub_path) for item in current]

            # Обычное поле или индекс
            if isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    raise KeyError(f"Неверный индекс '{part}' в списке на пути '{'.'.join(parts[:i+1])}'")
            elif hasattr(current, "__getitem__"):
                # Dict-подобный объект (BaseSchema или dict)
                try:
                    current = current[part]
                except KeyError:
                    raise KeyError(f"Поле '{part}' не найдено на пути '{'.'.join(parts[:i+1])}'")
            else:
                # Обычный объект
                try:
                    current = getattr(current, part)
                except AttributeError:
                    raise KeyError(f"Атрибут '{part}' не найден на пути '{'.'.join(parts[:i+1])}'")

        return current

    def to_dict(self) -> dict[str, Any]:
        """
        Синоним для model_dump() для совместимости.

        Возвращает:
            dict с данными сущности.
        """
        return self.model_dump()
