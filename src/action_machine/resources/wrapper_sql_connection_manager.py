# src/action_machine/resources/wrapper_sql_connection_manager.py
"""
Прокси-обёртка, запрещающая управление транзакциями на вложенных уровнях.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

WrapperSqlConnectionManager — прокси-обёртка вокруг реального SqlConnectionManager.
Создаётся автоматически при передаче connections в дочерние действия через
ToolsBox.run(). Обёртка запрещает дочернему действию управлять жизненным
циклом ресурса (open, begin, commit, rollback), но разрешает выполнять запросы
(execute).

Это гарантирует, что только корневое действие (владелец ресурса) управляет
транзакцией. Дочерние действия работают внутри той же транзакции, но не
могут случайно зафиксировать или откатить её.

═══════════════════════════════════════════════════════════════════════════════
ПРОКИДЫВАНИЕ ROLLUP
═══════════════════════════════════════════════════════════════════════════════

WrapperSqlConnectionManager сохраняет флаг rollup из оригинального менеджера.
Это обеспечивает сквозную передачу режима rollup через всю цепочку
вложенных действий:

    Корневое действие (rollup=True)
        │
        ├── connections["db"] = PostgresConnectionManager(rollup=True)
        │
        └── box.run(ChildAction, params, connections)
                │
                └── connections["db"] = WrapperSqlConnectionManager(original)
                        _rollup = original._rollup (True)
                        │
                        └── box.run(GrandChildAction, params, connections)
                                │
                                └── connections["db"] = WrapperSqlConnectionManager(wrapper)
                                        _rollup = wrapper._rollup (True)

На каждом уровне вложенности обёртка наследует rollup от предыдущего
уровня. Если корневой менеджер создан с rollup=True, все обёртки
на всех уровнях вложенности также будут иметь rollup=True.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    SqlConnectionManager (ABC)
        │
        ├── PostgresConnectionManager       ← реальный менеджер
        │       open()   → подключение к БД
        │       begin()  → BEGIN
        │       commit() → COMMIT (или ROLLBACK при rollup)
        │       execute()→ SQL-запрос
        │
        └── WrapperSqlConnectionManager        ← прокси
                open/begin/commit/rollback → TransactionProhibitedError
                execute()→ делегирует в реальный менеджер
                _rollup  → наследуется от оригинала

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Корневое действие создаёт реальный менеджер:
    db = PostgresConnectionManager(params, rollup=True)
    await db.open()
    await db.begin()

    # ToolsBox.run() оборачивает менеджер для дочернего действия:
    wrapper = WrapperSqlConnectionManager(db)
    wrapper.rollup   # → True (унаследовано)

    # Дочернее действие использует обёртку:
    await wrapper.execute("SELECT ...")  # → OK, делегируется в db
    await wrapper.commit()               # → TransactionProhibitedError
    await wrapper.open()                 # → TransactionProhibitedError
    await wrapper.begin()                # → TransactionProhibitedError

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TransactionProhibitedError — при попытке вызвать open(), begin(),
        commit() или rollback() на обёртке.
    HandleError — при ошибке выполнения SQL-запроса через execute().
"""

from typing import Any

from action_machine.model.exceptions import HandleError, TransactionProhibitedError
from action_machine.resources.sql_connection_manager import SqlConnectionManager


class WrapperSqlConnectionManager(SqlConnectionManager):
    """
    Прокси-обёртка для менеджера соединений, запрещающая управление транзакциями
    на вложенных уровнях, но разрешающая выполнение запросов.

    Создаётся автоматически при передаче connections в дочерние действия
    через ToolsBox._wrap_connections(). Флаг rollup наследуется от
    оригинального менеджера.

    Атрибуты:
        _connection_manager : SqlConnectionManager
            Реальный менеджер соединения (или другая обёртка верхнего уровня).
    """

    def __init__(self, connection_manager: SqlConnectionManager) -> None:
        """
        Инициализирует прокси-обёртку.

        Наследует флаг rollup из оригинального менеджера через
        super().__init__(rollup=connection_manager.rollup). Это обеспечивает
        сквозную передачу режима rollup через все уровни вложенности.

        Аргументы:
            connection_manager: реальный менеджер соединения (созданный
                выше по иерархии вложенности). Может быть как реальным
                менеджером (PostgresConnectionManager), так и другой
                обёрткой (WrapperSqlConnectionManager) при глубокой вложенности.
        """
        super().__init__(rollup=connection_manager.rollup)
        self._connection_manager = connection_manager

    async def open(self) -> None:
        """
        Запрещает открытие соединения из дочернего действия.

        Исключения:
            TransactionProhibitedError: всегда.
        """
        raise TransactionProhibitedError(
            "Открытие соединения разрешено только в том действии, где ресурс был создан. "
            "Текущее действие получило ресурс через прокси, поэтому open недоступен."
        )

    async def begin(self) -> None:
        """
        Запрещает начало транзакции из дочернего действия.

        Исключения:
            TransactionProhibitedError: всегда.
        """
        raise TransactionProhibitedError(
            "Управление транзакцией разрешено только владельцу соединения. "
            "Текущее действие получило ресурс через прокси, поэтому begin недоступен."
        )

    async def commit(self) -> None:
        """
        Запрещает фиксацию транзакции из дочернего действия.

        Не вызывает super().commit() — обёртка полностью запрещает
        управление транзакциями, включая rollup-перехват.

        Исключения:
            TransactionProhibitedError: всегда.
        """
        raise TransactionProhibitedError(
            "Фиксация транзакции разрешена только в том действии, где ресурс был создан. "
            "Текущее действие получило ресурс через прокси, поэтому commit недоступен."
        )

    async def rollback(self) -> None:
        """
        Запрещает откат транзакции из дочернего действия.

        Исключения:
            TransactionProhibitedError: всегда.
        """
        raise TransactionProhibitedError(
            "Откат транзакции разрешён только в том действии, где ресурс был создан. "
            "Текущее действие получило ресурс через прокси, поэтому rollback недоступен."
        )

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """
        Выполняет запрос, делегируя в реальный менеджер.

        Единственная разрешённая операция для дочерних действий. Запрос
        выполняется в контексте транзакции, открытой корневым действием.

        Аргументы:
            query: строка SQL-запроса.
            params: параметры запроса (опционально).

        Возвращает:
            Результат выполнения запроса от реального менеджера.

        Исключения:
            HandleError: при ошибке выполнения SQL-запроса.
        """
        try:
            return await self._connection_manager.execute(query, params)
        except Exception as e:
            raise HandleError(f"Ошибка выполнения SQL: {e}") from e

    def get_wrapper_class(self) -> type["SqlConnectionManager"] | None:
        """
        Возвращает класс обёртки для дальнейшей вложенности.

        При передаче уже обёрнутого менеджера в ещё более глубокий
        уровень вложенности, создаётся новый WrapperSqlConnectionManager,
        оборачивающий текущую обёртку. Флаг rollup прокидывается
        через всю цепочку.

        Возвращает:
            WrapperSqlConnectionManager — класс для создания следующего
            уровня обёртки.
        """
        return WrapperSqlConnectionManager
