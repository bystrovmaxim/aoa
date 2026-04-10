# src/action_machine/context/context_view.py
"""
ContextView — frozen-объект с контролируемым доступом к полям contextа.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ContextView — посредник между аспектом и полным Context. Создаётся машиной
(ActionProductMachine) для каждого вызова аспекта или обработчика ошибок,
у которого указан @context_requires. Принимает полный Context и frozenset
разрешённых ключей. Предоставляет единственный публичный method get(key),
который проверяет, что ключ входит в множество разрешённых, и делегирует
в context.resolve(key).

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИП МИНИМАЛЬНЫХ ПРИВИЛЕГИЙ
═══════════════════════════════════════════════════════════════════════════════

Аспект получает доступ ровно к тем полям contextа, которые объявил
через @context_requires. Обращение к любому другому полю — немедленный
ContextAccessError. Это:

- Делает зависимости от contextа явными и видимыми в коде.
- Предотвращает случайное чтение чувствительных данных.
- Упрощает тестирование: не нужно конструировать полный Context,
  достаточно замокать запрошенные поля.

═══════════════════════════════════════════════════════════════════════════════
FROZEN-ОБЪЕКТ
═══════════════════════════════════════════════════════════════════════════════

ContextView полностью неизменяем:
- __setattr__ выбрасывает AttributeError (кроме инициализации через
  object.__setattr__).
- __delattr__ выбрасывает AttributeError.
- Нет methodов модификации.
- __slots__ не используется, потому что переопределённый __setattr__
  в сочетании с __slots__ не видим для mypy и pylint при записи
  через object.__setattr__. Вместо этого используются аннотации
  атрибутов на уровне класса.

Это гарантирует, что аспект не может случайно изменить context
или state ContextView.

═══════════════════════════════════════════════════════════════════════════════
КАСТОМНЫЕ ПОЛЯ
═══════════════════════════════════════════════════════════════════════════════

UserInfo, RequestInfo и RuntimeInfo могут быть расширены наследниками
с дополнительными полями. ContextView не валидирует ключи на этапе
создания — проверяется только принадлежность ключа к allowed_keys.
Резолв значения делегируется в context.resolve(), который обходит
вложенные объекты через dot-path. Если поле не существует в contextе,
resolve() возвращает None.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Машина создаёт ContextView при вызове аспекта:
    ctx_view = ContextView(context, frozenset({"user.user_id", "user.roles"}))

    # Аспект использует ctx_view:
    user_id = ctx_view.get("user.user_id")    # → "agent_123"
    roles = ctx_view.get("user.roles")         # → ["admin", "user"]
    ip = ctx_view.get("request.client_ip")     # → ContextAccessError

    # Frozen:
    ctx_view.x = 1                              # → AttributeError
    del ctx_view._context                       # → AttributeError
"""

from typing import Any

from action_machine.core.exceptions import ContextAccessError


class ContextView:
    """
    Frozen-объект с контролируемым доступом к полям contextа.

    Создаётся машиной для каждого вызова аспекта или обработчика ошибок,
    у которого указан @context_requires. Предоставляет единственный
    публичный method get(key) для чтения разрешённых полей.

    Атрибуты (приватные, записываются через object.__setattr__):
        _context : Any
            Полный context выполнения. Используется для резолва значений.
        _allowed_keys : frozenset[str]
            Множество разрешённых ключей (dot-path), указанных
            в @context_requires. Только эти ключи можно читать через get().
    """

    # Аннотации атрибутов для mypy и pylint. Фактическая запись
    # происходит через object.__setattr__ в __init__, потому что
    # __setattr__ переопределён и запрещает запись.
    _context: Any
    _allowed_keys: frozenset[str]

    def __init__(self, context: Any, allowed_keys: frozenset[str]) -> None:
        """
        Инициализирует ContextView.

        Использует object.__setattr__ для записи приватных атрибутов,
        потому что __setattr__ переопределён и запрещает запись.

        Args:
            context: полный Context выполнения. ContextView делегирует
                     в context.resolve(key) при обращении к разрешённым
                     ключам.
            allowed_keys: frozenset строковых ключей (dot-path),
                          разрешённых через @context_requires.
                          Пустой frozenset означает, что доступ
                          запрещён ко всем полям.
        """
        object.__setattr__(self, "_context", context)
        object.__setattr__(self, "_allowed_keys", allowed_keys)

    def get(self, key: str) -> Any:
        """
        Returns значение поля contextа по ключу (dot-path).

        Checks, что ключ входит в множество разрешённых. Если да —
        делегирует в context.resolve(key) и возвращает результат.
        Если нет — выбрасывает ContextAccessError.

        Если ключ разрешён, но поле не существует в contextе
        (например, кастомное поле наследника, которое не было заполнено),
        context.resolve() возвращает None.

        Args:
            key: строка dot-path, например "user.user_id",
                 "request.trace_id", "user.extra.billing_plan".

        Returns:
            Значение поля из contextа. None если поле не существует.

        Raises:
            ContextAccessError: если ключ не входит в allowed_keys.
        """
        if key not in self._allowed_keys:
            raise ContextAccessError(key, self._allowed_keys)
        return self._context.resolve(key)

    @property
    def allowed_keys(self) -> frozenset[str]:
        """
        Returns множество разрешённых ключей (только чтение).

        Полезно для отладки и интроспекции: позволяет увидеть,
        какие поля contextа доступны в текущем аспекте.
        """
        return self._allowed_keys

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Запрещает запись атрибутов. ContextView полностью frozen.

        Raises:
            AttributeError: всегда.
        """
        raise AttributeError(
            f"ContextView является frozen-объектом. "
            f"Запись атрибута '{name}' запрещена."
        )

    def __delattr__(self, name: str) -> None:
        """
        Запрещает удаление атрибутов. ContextView полностью frozen.

        Raises:
            AttributeError: всегда.
        """
        raise AttributeError(
            f"ContextView является frozen-объектом. "
            f"Удаление атрибута '{name}' запрещено."
        )

    def __repr__(self) -> str:
        """Компактное строковое представление для отладки."""
        keys_str = ", ".join(sorted(self._allowed_keys))
        return f"ContextView(allowed_keys=[{keys_str}])"
