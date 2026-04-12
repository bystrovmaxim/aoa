# src/action_machine/contrib/postgres/postgres_connection_manager.py
"""
Реальный менеджер соединения для PostgreSQL.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

PostgresConnectionManager — конкретная реализация SqlConnectionManager для
PostgreSQL на базе библиотеки asyncpg. Выполняет непосредственную работу
с базой данных: открытие соединения, выполнение SQL-запросов, управление
транзакциями.

Проверки состояния соединения (открыто ли оно) выполняются в прокси-обёртке
WrapperSqlConnectionManager, а не здесь. PostgresConnectionManager отвечает
только за прямое взаимодействие с asyncpg.

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ROLLUP
═══════════════════════════════════════════════════════════════════════════════

PostgresConnectionManager полностью поддерживает режим rollup, унаследованный
от SqlConnectionManager. Параметр rollup передаётся в конструктор и
прокидывается в super().__init__(rollup=rollup).

Транзакционный цикл (asyncpg без явного BEGIN фиксирует каждый оператор отдельно):
- open()    → asyncpg.connect()
- begin()   → SQL ``BEGIN`` — дальнейшие execute в одной транзакции
- execute() → реальное выполнение SQL
- commit()  → ``COMMIT``, или при rollup=True — ROLLBACK вместо COMMIT
- rollback()→ ``ROLLBACK``

Механизм перехвата commit при rollup=True:
    PostgresConnectionManager.commit() проверяет self.rollup ПЕРВЫМ.
    Если rollup=True — вызывает self.rollback() и возвращает управление
    через return, НЕ выполняя код реального COMMIT. Это гарантирует,
    что при rollup=True команда COMMIT никогда не отправляется в БД.

    Этот подход надёжнее делегирования в super().commit(), потому что
    не зависит от того, как базовый класс обрабатывает возврат из
    await super().commit(). Каждый конкретный менеджер самостоятельно
    реализует перехват rollup в своём commit().

═══════════════════════════════════════════════════════════════════════════════
УПРАВЛЕНИЕ ТРАНЗАКЦИЯМИ
═══════════════════════════════════════════════════════════════════════════════

asyncpg.Connection не предоставляет methodов commit()/rollback() напрямую —
управление транзакциями через SQL: ``BEGIN``, ``COMMIT``, ``ROLLBACK``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Production — обычный режим:
    db = PostgresConnectionManager(
        connection_params={"host": "localhost", "database": "orders"},
    )
    await db.open()
    await db.begin()
    await db.execute("INSERT INTO orders (id, amount) VALUES ($1, $2)", (1, 100.0))
    await db.commit()  # → реальный COMMIT

    # Тестирование на production-базе — rollup:
    db = PostgresConnectionManager(
        connection_params={"host": "localhost", "database": "orders"},
        rollup=True,
    )
    await db.open()
    await db.begin()
    await db.execute("INSERT INTO orders (id, amount) VALUES ($1, $2)", (1, 100.0))
    await db.commit()  # → ROLLBACK (изменения не сохранены)

    # Передача в действие:
    result = await machine.run(
        context=ctx,
        action=CreateOrderAction(),
        params=order_params,
        connections={"db": db},
    )
"""

from typing import Any

import asyncpg

from action_machine.core.exceptions import HandleError
from action_machine.resource_managers.sql_connection_manager import SqlConnectionManager
from action_machine.resource_managers.wrapper_sql_connection_manager import (
    WrapperSqlConnectionManager,
)


class PostgresConnectionManager(SqlConnectionManager):
    """
    Реальный менеджер соединения для PostgreSQL.

    Использует asyncpg для подключения к базе данных. Поддерживает
    режим rollup: при rollup=True method commit() выполняет ROLLBACK
    вместо COMMIT.

    Перехват rollup реализован непосредственно в commit() этого класса:
    проверка self.rollup выполняется первой, и при True вызывается
    self.rollback() с немедленным return. Код реального COMMIT
    выполняется только при rollup=False.

    Атрибуты:
        _connection_params : dict[str, Any]
            Параметры подключения для asyncpg.connect()
            (host, port, user, password, database и т.д.).
        _conn : asyncpg.Connection | None
            Активное соединение с PostgreSQL. None до вызова open().
    """

    def __init__(
        self,
        connection_params: dict[str, Any],
        rollup: bool = False,
    ) -> None:
        """
        Инициализирует менеджер соединения с PostgreSQL.

        Args:
            connection_params: словарь parameters для asyncpg.connect().
                Обязательные ключи зависят от конфигурации PostgreSQL.
                Типичные: host, port, user, password, database.
            rollup: если True, commit() будет выполнять ROLLBACK вместо
                    COMMIT. Используется для безопасного тестирования
                    на production-базе. По умолчанию False.
        """
        super().__init__(rollup=rollup)
        self._connection_params = connection_params
        self._conn: asyncpg.Connection[asyncpg.Record] | None = None

    async def open(self) -> None:
        """
        Открывает соединение с PostgreSQL через asyncpg.connect().

        Raises:
            HandleError: при ошибке подключения к PostgreSQL.
                Оборачивает исходное исключение asyncpg с информативным
                сообщением.
        """
        try:
            self._conn = await asyncpg.connect(**self._connection_params)
        except Exception as e:
            raise HandleError(f"Ошибка подключения к PostgreSQL: {e}") from e

    async def begin(self) -> None:
        """
        Начинает транзакцию (SQL ``BEGIN``).

        Raises:
            HandleError: если соединение не открыто или ``BEGIN`` не выполнен.
        """
        if self._conn is None:
            raise HandleError("Соединение не открыто")
        try:
            await self._conn.execute("BEGIN")
        except Exception as e:
            raise HandleError(f"Ошибка при begin: {e}") from e

    async def commit(self) -> None:
        """
        Фиксирует транзакцию или откатывает при rollup=True.

        При rollup=True вызывает self.rollback() и немедленно возвращает
        управление. Команда COMMIT не отправляется в БД.

        При rollup=False отправляет SQL-команду COMMIT через asyncpg.
        asyncpg не имеет methodа connection.commit() — вместо этого
        используется прямая SQL-команда.

        Raises:
            HandleError: при ошибке выполнения COMMIT или если
                соединение не открыто.
        """
        # Перехват rollup: при True выполняем ROLLBACK вместо COMMIT
        # и возвращаем управление, не доходя до кода реального COMMIT.
        if self.rollup:
            await self.rollback()
            return

        # rollup=False — выполняем реальный COMMIT
        if self._conn is None:
            raise HandleError("Соединение не открыто")
        try:
            await self._conn.execute("COMMIT")
        except Exception as e:
            raise HandleError(f"Ошибка при commit: {e}") from e

    async def rollback(self) -> None:
        """
        Откатывает транзакцию.

        asyncpg не имеет methodа connection.rollback() — вместо этого
        отправляется SQL-команда ROLLBACK напрямую.

        Raises:
            HandleError: при ошибке выполнения ROLLBACK или если
                соединение не открыто.
        """
        if self._conn is None:
            raise HandleError("Соединение не открыто")
        try:
            await self._conn.execute("ROLLBACK")
        except Exception as e:
            raise HandleError(f"Ошибка при rollback: {e}") from e

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """
        Выполняет SQL-запрос через asyncpg.

        После ``begin()`` запросы выполняются в одной транзакции; при
        rollup=True ``commit()`` откатывает её.

        Args:
            query: строка SQL-запроса.
            params: параметры запроса (опционально). Передаются
                    как позиционные аргументы в asyncpg.execute().

        Returns:
            Результат выполнения запроса от asyncpg.

        Raises:
            HandleError: при ошибке выполнения SQL или если соединение
                не открыто.
        """
        if self._conn is None:
            raise HandleError("Соединение не открыто")
        try:
            return await self._conn.execute(query, *params if params else ())
        except Exception as e:
            raise HandleError(f"Ошибка выполнения SQL: {e}") from e

    def get_wrapper_class(self) -> type[SqlConnectionManager] | None:
        """
        Returns класс прокси-обёртки для передачи в дочерние действия.

        WrapperSqlConnectionManager запрещает дочерним действиям управлять
        транзакциями (open/commit/rollback), но разрешает выполнять
        запросы (execute). Флаг rollup прокидывается через обёртку.

        Returns:
            WrapperSqlConnectionManager — класс прокси-обёртки.
        """
        return WrapperSqlConnectionManager
