try:
    import asyncpg  # noqa: F401
except ImportError:
    raise ImportError(
        "Для использования action_machine.contrib.postgres "
        "установите зависимость: pip install action-machine[postgres]"
    ) from None

from .postgres_connection_manager import PostgresConnectionManager

__all__ = ["PostgresConnectionManager"]