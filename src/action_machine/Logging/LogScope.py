# ActionMachine/Logging/LogScope.py
"""
Скоуп логирования — обёртка над словарём произвольных ключей,
описывающая «где мы находимся» в момент вызова логера.

Машина заполняет скоуп в момент создания. Для разных мест
(action, aspect, plugin, global_start и т.п.) скоуп может иметь
разную длину и разный набор ключей. Шаги пути могут значить
разное в зависимости от контекста.

LogScope не имеет фиксированных полей — никаких action_name,
aspect_name как атрибутов класса. Всё — ключи внутреннего словаря.

LogScope наследует collections.abc.Mapping, что автоматически
предоставляет методы __contains__, get, keys, values, items
на основе трёх обязательных: __getitem__, __iter__, __len__.
Это сокращает количество явно написанных методов и обеспечивает
единообразный dict-подобный интерфейс.

Метод as_dotpath() склеивает значения словаря через точку
в порядке вставки (dict в Python 3.7+ сохраняет порядок).
Результат кешируется лениво: при первом вызове вычисляется,
при повторных — возвращается из кеша. Скоуп считается
неизменяемым после создания — мутация не инвалидирует кеш.

Примеры скоупов разной длины и содержания:

На уровне action (global_start):
>>> scope = LogScope(action="ProcessOrderAction")
>>> scope.as_dotpath()
'ProcessOrderAction'

На уровне aspect (before):
>>> scope = LogScope(action="ProcessOrderAction", aspect="validate_user", event="before")
>>> scope.as_dotpath()
'ProcessOrderAction.validate_user.before'

На уровне вложенного action внутри аспекта:
>>> scope = LogScope(action="ProcessOrderAction", aspect="charge", nested_action="ChargeCardAction")
>>> scope.as_dotpath()
'ProcessOrderAction.charge.ChargeCardAction'

На уровне plugin:
>>> scope = LogScope(action="ProcessOrderAction", plugin="MetricsPlugin", event="global_finish")
>>> scope.as_dotpath()
'ProcessOrderAction.MetricsPlugin.global_finish'
"""

from collections.abc import Iterator, Mapping


class log_scope(Mapping[str, str]):
    """
    Обёртка над словарём произвольных ключей, описывающая
    местоположение в конвейере выполнения.

    Наследует collections.abc.Mapping[str, str], реализуя три обязательных
    метода: __getitem__, __iter__, __len__. Остальные методы
    dict-подобного интерфейса (__contains__, get, keys, values,
    items) предоставляются автоматически абстрактным базовым
    классом Mapping.

    Машина решает, какие ключи и значения поместить в скоуп.
    Разные ситуации — разные ключи — разная длина пути.
    LogScope не знает и не должен знать, какие ключи в нём есть.

    Скоуп неизменяем после создания. Метод as_dotpath()
    кешируется лениво при первом вызове.
    """

    _data: dict[str, str]
    _cached_path: str | None

    def __init__(self, **kwargs: str) -> None:
        """
        Создаёт скоуп из произвольного набора именованных аргументов.

        Все значения должны быть строками. Порядок аргументов
        определяет порядок элементов в dotpath.

        Аргументы:
            **kwargs: произвольные ключи и их строковые значения.
                Например: action="ProcessOrderAction",
                aspect="validate_user", event="before".

        Пример:
            >>> scope = LogScope(action="MyAction", aspect="load_data")
            >>> scope["action"]
            'MyAction'
            >>> scope.as_dotpath()
            'MyAction.load_data'
        """
        self._data: dict[str, str] = dict(kwargs)
        self._cached_path: str | None = None

    # ------------------------------------------------------------------
    # Три обязательных метода Mapping.
    # Всё остальное (__contains__, get, keys, values, items)
    # Mapping предоставляет автоматически на основе этих трёх.
    # ------------------------------------------------------------------

    def __getitem__(self, key: str) -> str:
        """
        Возвращает значение по ключу.

        Аргументы:
            key: имя ключа в скоупе.

        Возвращает:
            Строковое значение.

        Исключения:
            KeyError: если ключ отсутствует в скоупе.

        Пример:
            >>> scope = LogScope(action="MyAction")
            >>> scope["action"]
            'MyAction'
        """
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        """
        Возвращает итератор по ключам скоупа в порядке добавления.

        Mapping использует __iter__ для автоматической реализации
        keys(), values(), items(), __contains__ и get().

        Возвращает:
            Итератор по строковым ключам.

        Пример:
            >>> scope = LogScope(action="MyAction", aspect="load")
            >>> list(scope)
            ['action', 'aspect']
        """
        return iter(self._data)

    def __len__(self) -> int:
        """
        Возвращает количество ключей в скоупе.

        Возвращает:
            Целое число — количество ключей.

        Пример:
            >>> scope = LogScope(action="MyAction", aspect="load")
            >>> len(scope)
            2
        """
        return len(self._data)

    # ------------------------------------------------------------------
    # Бизнес-методы LogScope (не связаны с Mapping).
    # ------------------------------------------------------------------

    def as_dotpath(self) -> str:
        """
        Возвращает все значения скоупа, склеенные через точку
        в порядке добавления.

        Результат кешируется при первом вызове. Повторные вызовы
        возвращают закешированное значение без пересчёта.

        Пустые значения пропускаются при склейке.

        Возвращает:
            Строка вида "ProcessOrderAction.validate_user.before".
            Пустая строка если скоуп пуст.

        Пример:
            >>> LogScope(action="MyAction", aspect="save").as_dotpath()
            'MyAction.save'
            >>> LogScope().as_dotpath()
            ''
        """
        if self._cached_path is None:
            self._cached_path = ".".join(value for value in self._data.values() if value)
        return self._cached_path

    def to_dict(self) -> dict[str, str]:
        """
        Возвращает копию внутреннего словаря.

        Копия гарантирует, что внешний код не может
        изменить содержимое скоупа.

        Возвращает:
            Новый словарь с ключами и значениями скоупа.

        Пример:
            >>> scope = LogScope(action="MyAction", event="start")
            >>> scope.to_dict()
            {'action': 'MyAction', 'event': 'start'}
        """
        return dict(self._data)

    def __repr__(self) -> str:
        """
        Строковое представление скоупа для отладки.

        Возвращает:
            Строка вида LogScope(action='MyAction', aspect='load').

        Пример:
            >>> repr(LogScope(action="MyAction"))
            "LogScope(action='MyAction')"
        """
        pairs = ", ".join(f"{k}='{v}'" for k, v in self._data.items())
        return f"LogScope({pairs})"
