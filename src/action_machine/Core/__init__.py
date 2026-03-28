# src/action_machine/core/__init__.py
"""
Пакет ядра ActionMachine.

Содержит базовые классы, протоколы, миксины, машины выполнения,
координатор метаданных, исключения и вспомогательные утилиты.

MetadataBuilder вынесен в отдельный подпакет action_machine.metadata
и НЕ реэкспортируется из core. Импорт выполняется напрямую:

    from action_machine.metadata import MetadataBuilder
"""