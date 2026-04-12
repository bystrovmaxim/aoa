# src/action_machine/resource_managers/sql_connection_manager.py
"""
Интерфейс менеджера соединений с базами данных.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

SqlConnectionManager — абстрактный базовый класс для менеджеров SQL-соединений
с транзакциями. Определяет контракт:
open(), begin(), commit(), rollback(), execute().

Наследует BaseResourceManager, что обеспечивает:
- Обязательность декоратора @meta с описанием.
- Поддержку обёрток (get_wrapper_class) для дочерних действий.
- Проверку rollup-поддержки (check_rollup_support).

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖКА ROLLUP
═══════════════════════════════════════════════════════════════════════════════

SqlConnectionManager полностью поддерживает режим rollup. Параметр rollup
передаётся в конструктор и сохраняется в атрибуте self._rollup.

Когда rollup=True, метод commit() вызывает self.rollback() вместо
реальной фиксации транзакции. Чтобы изменения действительно жили в одной
транзакции и откатывались, перед мутациями вызывают begin() после open();
без begin() драйверы вроде asyncpg фиксируют операторы по одному (autocommit).

Метод check_rollup_support() переопределён и возвращает True —
все наследники SqlConnectionManager автоматически поддерживают rollup.

Конкретные реализации (PostgresConnectionManager и др.) прокидывают
параметр rollup в super().__init__(rollup=rollup).

═══════════════════════════════════════════════════════════════════════════════
УСТОЙЧИВОСТЬ PROPERTY rollup
═══════════════════════════════════════════════════════════════════════════════

Property rollup использует getattr(self, "_rollup", False) вместо
прямого обращения к self._rollup. Это обеспечивает корректную работу
с наследниками, чей __init__ не вызывает super().__init__() —
например, мок-классы в тестах, которые заменяют методы на AsyncMock
в своём __init__ без вызова родительского конструктора. В таких случаях
rollup возвращает False (безопасное значение по умолчанию).

═══════════════════════════════════════════════════════════════════════════════
ЖИЗНЕННЫЙ ЦИКЛ ROLLUP
═══════════════════════════════════════════════════════════════════════════════

    # Вызывающий код создаёт менеджер с rollup=True:
    db = PostgresConnectionManager(params, rollup=True)

    # Аспект работает как обычно:
    await db.open()
    await db.begin()                   # → одна транзакция для всех execute
    await db.execute("INSERT ...")
    await db.execute("UPDATE ...")
    await db.commit()                  # → ROLLBACK (вместо COMMIT!)

    # Все изменения откачены, production-база не затронута.

═══════════════════════════════════════════════════════════════════════════════
ПЕРЕДАЧА ROLLUP В ДОЧЕРНИЕ ДЕЙСТВИЯ
═══════════════════════════════════════════════════════════════════════════════

WrapperSqlConnectionManager при создании обёртки сохраняет флаг rollup
из оригинального менеджера. Дочерние действия, получающие connections
через обёртку, также работают в режиме rollup — цепочка не прерывается.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    BaseResourceManager (ABC)
        │
        └── SqlConnectionManager (ABC)
                │   _rollup: bool
                │   check_rollup_support() → True
                │   commit() → rollback() если _rollup=True
                │
                ├── PostgresConnectionManager
                │       __init__(params, rollup=False)
                │       begin() → старт транзакции (корневое действие)
                │
                └── WrapperSqlConnectionManager (прокси)
                        __init__(connection_manager)
                        _rollup берётся из оригинала
                        begin/open/commit/rollback запрещены

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Production — обычный режим:
    db = PostgresConnectionManager(params, rollup=False)
    await db.open()
    await db.begin()
    await db.execute("INSERT INTO orders ...")
    await db.commit()  # → COMMIT

    # Тестирование — rollup:
    db = PostgresConnectionManager(params, rollup=True)
    await db.open()
    await db.begin()
    await db.execute("INSERT INTO orders ...")
    await db.commit()  # → ROLLBACK (данные не сохранены)
"""

from abc import abstractmethod
from typing import Any

from .base_resource_manager import BaseResourceManager


class SqlConnectionManager(BaseResourceManager):
    """
    Базовый класс для менеджеров SQL-соединений с транзакциями.

    Определяет контракт транзакционного управления: open, begin,
    commit, rollback, execute. Поддерживает режим rollup через параметр
    конструктора.

    Атрибуты:
        _rollup : bool
            Флаг режима автоотката. Если True, метод commit() выполняет
            rollback() вместо реальной фиксации транзакции.
            Инициализируется в __init__. Если наследник не вызывает
            super().__init__(), property rollup возвращает False.
    """

    def __init__(self, rollup: bool = False) -> None:
        """
        Инициализирует менеджер соединений.

        Аргументы:
            rollup: если True, commit() будет вызывать rollback() вместо
                    реальной фиксации. Используется для безопасного
                    тестирования на production-базе. По умолчанию False.
        """
        self._rollup: bool = rollup

    @property
    def rollup(self) -> bool:
        """
        Возвращает текущий флаг rollup.

        Использует getattr с fallback на False для устойчивости
        к наследникам, чей __init__ не вызывает super().__init__().
        Это типичная ситуация в тестах, где мок-классы заменяют
        методы на AsyncMock в своём конструкторе без вызова
        родительского __init__.

        Возвращает:
            bool — True если rollup активен, False по умолчанию.
        """
        return getattr(self, "_rollup", False)

    def check_rollup_support(self) -> bool:
        """
        Подтверждает поддержку режима rollup.

        SqlConnectionManager и все его наследники поддерживают rollup,
        так как управляют транзакционными ресурсами с операциями
        commit/rollback.

        Возвращает:
            True — всегда.
        """
        return True

    @abstractmethod
    async def open(self) -> None:
        """Открывает соединение с ресурсом."""
        pass

    @abstractmethod
    async def begin(self) -> None:
        """Начинает транзакцию (после open, до мутаций в одной транзакции)."""
        pass

    async def commit(self) -> None:
        """
        Фиксирует транзакцию или откатывает её в режиме rollup.

        Если self.rollup is True — вызывает self.rollback() вместо
        реальной фиксации. Это ключевой механизм безопасного тестирования:
        весь конвейер бизнес-логики выполняется полностью, но изменения
        в базе данных не сохраняются.

        Конкретные реализации (PostgresConnectionManager) вызывают
        super().commit() в начале своей реализации. При rollup=True
        super().commit() вызывает self.rollback() и возвращает управление —
        код после super().commit() в наследнике НЕ выполняется.

        Для обеспечения этого поведения, конкретные реализации ОБЯЗАНЫ
        проверять возврат из super().commit() или использовать паттерн:

            async def commit(self) -> None:
                if self.rollup:
                    await self.rollback()
                    return
                # ... реальный COMMIT ...
        """
        if self.rollup:
            await self.rollback()
            return

    @abstractmethod
    async def rollback(self) -> None:
        """Откатывает транзакцию."""
        pass

    @abstractmethod
    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """
        Выполняет запрос к ресурсу.

        Аргументы:
            query: строка запроса (SQL или другой язык запросов ресурса).
            params: параметры запроса (опционально).

        Возвращает:
            Результат выполнения запроса (тип зависит от конкретного ресурса).
        """
        pass
