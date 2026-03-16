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

Структура метода resolve:
    Три стратегии навигации по вложенным объектам (ReadableMixin,
    dict, generic) реализованы как отдельные статические методы:
        - _resolve_step_readable  → обход через __getitem__
        - _resolve_step_dict      → обход через dict-доступ
        - _resolve_step_generic   → обход через getattr
    Единый метод _resolve_one_step выбирает стратегию по типу
    текущего объекта. Основной метод resolve вызывает _resolve_one_step
    в цикле и управляет кешем.

    Это позволяет:
        1. Тестировать каждую стратегию навигации отдельно.
        2. Легко добавлять новые типы навигации (например, для NamedTuple) —
           достаточно написать новый _resolve_step_* и добавить проверку
           в _resolve_one_step.
        3. Поддерживать низкую цикломатическую сложность каждого компонента.

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
# Используется внутри _resolve_step_generic и _resolve_step_readable,
# чтобы корректно обрабатывать None-значения
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

    # ---------- Стратегии навигации для resolve ----------
    #
    # Каждая стратегия навигации — это @staticmethod,
    # возвращающий найденное значение или _SENTINEL если шаг не удался.
    #
    # Метод _resolve_one_step выбирает стратегию по isinstance и
    # делегирует вызов. Это единственная точка расширения:
    # чтобы добавить поддержку нового типа (например, NamedTuple),
    # достаточно:
    #   1. Написать _resolve_step_namedtuple(...) → @staticmethod
    #   2. Добавить isinstance-проверку в _resolve_one_step
    #
    # Контракт стратегий:
    #   Аргументы:
    #       current — текущий объект на данном шаге обхода.
    #       segment — имя ключа/атрибута для перехода.
    #   Возвращает:
    #       Найденное значение, если шаг успешен.
    #       _SENTINEL, если ключ/атрибут не найден.

    @staticmethod
    def _resolve_step_readable(
        current: 'ReadableMixin',
        segment: str,
    ) -> object:
        """
        Шаг навигации для объектов с ReadableMixin.

        Использует __getitem__ для доступа к полю по имени.
        Если ключ не найден (KeyError), возвращает _SENTINEL.

        Аргументы:
            current: объект с ReadableMixin (Context, UserInfo,
                     RequestInfo, EnvironmentInfo, BaseParams, BaseResult).
            segment: имя поля для перехода.

        Возвращает:
            Значение поля, или _SENTINEL если поле не существует.

        Пример:
            >>> user = UserInfo(user_id="42")
            >>> ReadableMixin._resolve_step_readable(user, "user_id")
            '42'
            >>> ReadableMixin._resolve_step_readable(user, "missing")
            <_SENTINEL>
        """
        try:
            return current[segment]
        except KeyError:
            return _SENTINEL

    @staticmethod
    def _resolve_step_dict(
        current: dict,  # type: ignore[type-arg]
        segment: str,
    ) -> object:
        """
        Шаг навигации для обычных словарей.

        Проверяет наличие ключа через оператор in.
        Если ключ есть — возвращает значение, иначе _SENTINEL.

        Аргументы:
            current: словарь (например, extra в UserInfo, или вложенный dict).
            segment: имя ключа для перехода.

        Возвращает:
            Значение по ключу, или _SENTINEL если ключ отсутствует.

        Пример:
            >>> ReadableMixin._resolve_step_dict({"org": "acme"}, "org")
            'acme'
            >>> ReadableMixin._resolve_step_dict({"org": "acme"}, "missing")
            <_SENTINEL>
        """
        if segment in current:
            return current[segment]
        return _SENTINEL

    @staticmethod
    def _resolve_step_generic(
        current: object,
        segment: str,
    ) -> object:
        """
        Шаг навигации для произвольных объектов через getattr.

        Используется как fallback для объектов, которые не являются
        ни ReadableMixin, ни dict. Например, для объектов сторонних
        библиотек или для будущих расширений (NamedTuple и т.д.).

        Аргументы:
            current: произвольный объект.
            segment: имя атрибута для перехода.

        Возвращает:
            Значение атрибута, или _SENTINEL если атрибут не существует.

        Пример:
            >>> class Obj:
            ...     x = 42
            >>> ReadableMixin._resolve_step_generic(Obj(), "x")
            42
            >>> ReadableMixin._resolve_step_generic(Obj(), "missing")
            <_SENTINEL>
        """
        return getattr(current, segment, _SENTINEL)

    def _resolve_one_step(
        self,
        current: object,
        segment: str,
    ) -> object:
        """
        Выполняет один шаг навигации, выбирая стратегию по типу текущего объекта.

        Порядок проверки isinstance определяет приоритет стратегий:
            1. ReadableMixin — объекты с dict-подобным доступом через __getitem__.
               Проверяется первым, потому что ReadableMixin-объекты
               также имеют атрибуты (getattr работал бы), но __getitem__
               точнее отражает контракт протокола.
            2. dict — обычные словари (extra, вложенные структуры).
               Проверяется вторым, потому что dict не наследует ReadableMixin.
            3. Любой другой объект — fallback через getattr.
               Покрывает все остальные случаи.

        Аргументы:
            current: текущий объект на данном шаге обхода.
            segment: имя ключа/атрибута для перехода к следующему объекту.

        Возвращает:
            Найденное значение, или _SENTINEL если шаг не удался.

        Пример:
            >>> ctx = Context(user=UserInfo(user_id="42"))
            >>> ctx._resolve_one_step(ctx, "user")
            UserInfo(user_id='42', ...)
            >>> ctx._resolve_one_step({"key": "val"}, "key")
            'val'
        """
        if isinstance(current, ReadableMixin):
            return self._resolve_step_readable(current, segment)
        if isinstance(current, dict):
            return self._resolve_step_dict(current, segment)
        return self._resolve_step_generic(current, segment)

    # ---------- Основной метод resolve ----------

    def resolve(self, dotpath: str, default: object = None) -> object:
        """
        Разрешает dot-path строку, обходя вложенные объекты по цепочке.

        Поддерживает три типа промежуточных объектов на каждом шаге
        (через метод _resolve_one_step):
            1. Объект с ReadableMixin — используется __getitem__ (obj[segment]).
            2. dict — используется dict[segment].
            3. Любой другой объект — используется getattr(obj, segment).

        Если на любом шаге цепочки значение не найдено (_resolve_one_step
        вернул _SENTINEL), метод возвращает default без выброса исключения.

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
        # На каждом шаге _resolve_one_step выбирает стратегию навигации
        # по типу текущего объекта и возвращает значение или _SENTINEL.
        segments = dotpath.split('.')
        current: object = self

        for segment in segments:
            current = self._resolve_one_step(current, segment)
            if current is _SENTINEL:
                # Путь оборвался — кешируем default и возвращаем.
                cache[dotpath] = default
                return default

        # Сохраняем результат в кеш и возвращаем.
        cache[dotpath] = current
        return current
