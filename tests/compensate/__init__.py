# tests/compensate/__init__.py
"""
Пакет тестов механизма компенсации (Saga) ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит все тесты, проверяющие механизм компенсации — паттерн Saga,
реализованный в ActionMachine. Тесты организованы по аспектам
функциональности:

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА ТЕСТОВ
═══════════════════════════════════════════════════════════════════════════════

test_compensate_decorator.py
    Валидации декоратора @compensate при определении класса (import-time):
    корректные аргументы, некорректные типы, суффикс имени, сигнатура.

test_compensate_metadata.py
    Сборка метаданных через MetadataBuilder и валидация инвариантов:
    collect_compensators, validate_compensators, ClassMetadata API.

test_compensate_graph.py
    Граф в GateCoordinator: узлы "compensator", рёбра "has_compensator"
    и "requires_context", dependency tree.

test_saga_rollback.py
    Ядро механизма — размотка стека SagaFrame в обратном порядке
    через ActionProductMachine._rollback_saga(): порядок вызовов,
    корректность данных (params, state_before, state_after, error).

test_saga_errors.py
    Молчаливое подавление ошибок компенсаторов: ошибка не прерывает
    размотку, все компенсаторы получают шанс выполниться, @on_error
    получает оригинальную ошибку аспекта.

test_saga_events.py
    Типизированные события плагинов: SagaRollbackStartedEvent,
    SagaRollbackCompletedEvent, BeforeCompensateAspectEvent,
    AfterCompensateAspectEvent, CompensateFailedEvent.

test_saga_rollup.py
    Поведение при rollup=True: компенсаторы не вызываются,
    Saga-события не эмитируются.

test_saga_order.py
    Порядок обработки ошибки: компенсация выполняется ДО @on_error.

test_saga_nested.py
    Вложенные вызовы через box.run(): изоляция стеков на каждом
    уровне вложенности, взаимодействие с try/except в аспектах.

test_saga_integration.py
    Полные E2E-сценарии: несколько аспектов + компенсаторы + @on_error,
    компенсатор с @context_requires.
"""
