# ActionMachine/Core/ReadableMixin.py
"""
Миксин для реализации протокола ReadableDataProtocol
на основе атрибутов объекта. Предназначен для использования в dataclass-классах,
наследующих BaseParams и BaseResult, а также в Context-компонентах
(UserInfo, RequestInfo, EnvironmentInfo).

Обеспечивает два уровня доступа к данным:
1. Плоский доступ — через __getitem__, get, keys и т.д.
2. Dot-path доступ — через метод resolve, который обходит вложенные объекты
   по цепочке ключей, разделённых точкой.

Dot-path разрешение работает единообразно для всех объектов,
наследующих ReadableMixin: Context, UserInfo, RequestInfo, EnvironmentInfo,
BaseParams, BaseResult. Результаты resolve кешируются лениво
в словаре _resolve_cache, который живёт столько же, сколько сам объект.

Кеш инициализируется через object.__setattr__, что позволяет
корректно работать с frozen dataclass (frozen=True запрещает
обычное присваивание через self.attr = value, но
object.__setattr__ обходит это ограничение для служебных полей).

Пример:
    >>> from ActionMachine.Context.Context import Context
    >>> from ActionMachine.Context.UserInfo import UserInfo
    >>> user = UserInfo(user_id="agent_1", roles=["admin"])
    >>> ctx = Context(user=user)
    >>> ctx.resolve("user.user_id")
    'agent_1'
    >>> ctx.resolve("user.nonexistent", default="<none>")
    '<none>'
"""

# Сентинел для отличия «атрибут не найден» от «атрибут равен None».
# Используется внутри resolve, чтобы корректно обрабатывать None-значения
# и не путать их с отсутствием ключа.
_SENTINEL = object()


class ReadableMixin:
    """
    Реализует ReadableDataProtocol через атрибуты объекта.

    Позволяет обращаться к полям dataclass как через точку (obj.field),
    так и через dict-подобный доступ (obj["field"]).

    Метод resolve обеспечивает навигацию по вложенным объектам
    через dot-path строки вида "user.roles" или "request.trace_id".
    Результаты кешируются в _resolve_cache для повторных вызовов.

    Кеш создаётся через object.__setattr__ для совместимости
    с frozen dataclass.
    """

    _resolve_cache: dict[str, object]

    def __getitem__(self, key: str) -> object:
        """
        Возвращает значение атрибута по имени ключа.

        Аргументы:
            key: имя атрибута.

        Возвращает:
            Значение атрибута.

        Исключения:
            KeyError: если атрибут не существует.
        """
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e

    def __contains__(self, key: str) -> bool:
        """
        Проверяет наличие атрибута по имени.

        Аргументы:
            key: имя атрибута.

        Возвращает:
            True если атрибут существует, иначе False.
        """
        return hasattr(self, key)

    def get(self, key: str, default: object = None) -> object:
        """
        Безопасное получение значения атрибута с дефолтом.

        Аргументы:
            key: имя атрибута.
            default: значение по умолчанию, если атрибут отсутствует.

        Возвращает:
            Значение атрибута или default.
        """
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """
        Возвращает список имён всех публичных полей объекта.

        Публичными считаются все атрибуты, имя которых
        не начинается с символа подчёркивания '_'.

        Возвращает:
            Список строк — имена публичных полей.
        """
        return [k for k in vars(self) if not k.startswith('_')]

    def values(self) -> list[object]:
        """
        Возвращает список значений всех публичных полей объекта.

        Возвращает:
            Список значений.
        """
        return [self[k] for k in self.keys()]

    def items(self) -> list[tuple[str, object]]:
        """
        Возвращает список пар (ключ, значение) для всех публичных полей.

        Возвращает:
            Список кортежей (имя_поля, значение).
        """
        return [(k, self[k]) for k in self.keys()]

    def resolve(self, dotpath: str, default: object = None) -> object:
        """
        Разрешает dot-path строку, обходя вложенные объекты по цепочке.

        Поддерживает три типа промежуточных объектов на каждом шаге:
        1. Объект с ReadableMixin — используется __getitem__ (obj[segment]).
        2. dict — используется dict[segment].
        3. Любой другой объект — используется getattr(obj, segment).

        Если на любом шаге цепочки значение не найдено (KeyError, отсутствие
        атрибута), метод возвращает default без выброса исключения.

        Результаты кешируются в словаре _resolve_cache. При первом вызове
        resolve словарь создаётся лениво через object.__setattr__,
        что позволяет работать с frozen dataclass (frozen=True).
        При повторном вызове с тем же dotpath результат возвращается из кеша.

        Аргументы:
            dotpath: строка вида "user.user_id" или "request.tags.ab_variant".
                     Каждый сегмент разделён точкой и обозначает шаг
                     навигации по вложенным объектам.
            default: значение, возвращаемое если путь не удалось разрешить.
                     По умолчанию None.

        Возвращает:
            Найденное значение на конце пути, или default если путь
            не удалось пройти до конца.

        Пример:
            >>> from ActionMachine.Context.UserInfo import UserInfo
            >>> user = UserInfo(user_id="42", roles=["admin"], extra={"org": "acme"})
            >>> user.resolve("user_id")
            '42'
            >>> user.resolve("extra.org")
            'acme'
            >>> user.resolve("extra.nonexistent", default="<none>")
            '<none>'
        """
        # Ленивая инициализация кеша при первом вызове resolve.
        # Используем object.__setattr__ вместо self._resolve_cache = {}
        # потому что frozen dataclass запрещает обычное присваивание.
        # object.__setattr__ обходит __setattr__ переопределённый
        # frozen dataclass и позволяет установить служебный атрибут.
        try:
            cache = self.__dict__['_resolve_cache']
        except KeyError:
            cache = {}
            object.__setattr__(self, '_resolve_cache', cache)

        # Проверяем кеш: если dotpath уже разрешался ранее, возвращаем результат.
        if dotpath in cache:
            return cache[dotpath]

        # Разбиваем путь на сегменты и обходим цепочку.
        segments = dotpath.split('.')
        current: object = self

        for segment in segments:
            # Шаг 1: объект с ReadableMixin — используем __getitem__
            if isinstance(current, ReadableMixin):
                try:
                    current = current[segment]
                except KeyError:
                    cache[dotpath] = default
                    return default

            # Шаг 2: обычный dict — используем dict-доступ
            elif isinstance(current, dict):
                if segment in current:
                    current = current[segment]
                else:
                    cache[dotpath] = default
                    return default

            # Шаг 3: любой другой объект — используем getattr
            else:
                value = getattr(current, segment, _SENTINEL)
                if value is _SENTINEL:
                    cache[dotpath] = default
                    return default
                current = value

        # Сохраняем результат в кеш и возвращаем.
        cache[dotpath] = current
        return current