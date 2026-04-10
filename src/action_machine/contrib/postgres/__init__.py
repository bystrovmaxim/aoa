"""Contrib-пакет для работы с PostgreSQL через asyncpg.

AI-CORE-BEGIN
ROLE: module __init__
CONTRACT: Keep runtime behavior unchanged; documentation defines key contracts and flow for humans and AI.
INVARIANTS: Preserve declared interfaces and validation semantics.
FLOW: declaration -> inspector/coordinator snapshot -> runtime consumption.
AI-CORE-END
"""
try:
    import asyncpg  # noqa: F401
except ImportError:
    raise ImportError(
        "Для использования action_machine.contrib.postgres "
        "установите зависимость: pip install action-machine[postgres]"
    ) from None

from .postgres_connection_manager import PostgresConnectionManager

__all__ = ["PostgresConnectionManager"]
