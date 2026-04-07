# src/action_machine/core/saga_frame.py
"""
Фрейм стека компенсации (Saga).

Каждый успешно выполненный regular-аспект порождает один SagaFrame.
Фреймы накапливаются в локальном стеке внутри _execute_regular_aspects().
При возникновении ошибки в любом аспекте стек разматывается в обратном
порядке методом _rollback_saga().

Архитектура:
    Фрейм хранит только данные, УНИКАЛЬНЫЕ для конкретного аспекта:
    - state_before: состояние до выполнения аспекта
    - state_after: состояние после выполнения аспекта (None если чекер отклонил)
    - compensator: метаданные компенсатора (None если не определён)
    - aspect_name: имя аспекта для диагностики и событий плагинов

    Данные, ОБЩИЕ для всего конвейера одного _run_internal (params,
    connections, context, box), НЕ дублируются в каждом фрейме —
    они передаются в _rollback_saga() как аргументы.

Изоляция стеков:
    Каждый вызов _run_internal создаёт СВОЙ локальный стек.
    Глобального стека нет. При вложенных вызовах (box.run(ChildAction))
    дочерний Action имеет собственный стек, который разматывается
    независимо от родительского. Это гарантирует корректное поведение
    при перехвате исключений дочернего Action через try/except
    в аспекте родителя.

Связь с CompensatorMeta:
    Поле compensator ссылается на CompensatorMeta из class_metadata.
    Если для аспекта не определён компенсатор, поле равно None —
    такой фрейм пропускается при размотке (счётчик skipped).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.core.class_metadata import CompensatorMeta


@dataclass(frozen=True)
class SagaFrame:
    """
    Один фрейм стека компенсации.

    Создаётся после успешного выполнения regular-аспекта
    (аспект вернул dict, независимо от результата чекера).

    Когда фрейм создаётся:
        - Аспект вернул dict, чекеры пройдены → state_after = новый state.
        - Аспект вернул dict, чекер отклонил → state_after = None.
          Побочный эффект МОГ произойти (например, HTTP-запрос к платёжному
          шлюзу уже отправлен), поэтому фрейм создаётся для возможной
          компенсации.

    Когда фрейм НЕ создаётся:
        - Аспект бросил исключение до возврата dict.
          Побочный эффект не гарантирован, компенсировать нечего.

    Атрибуты:
        compensator:
            Метаданные компенсатора для этого аспекта.
            None — если для аспекта не определён декоратор @compensate.
            Фреймы без компенсатора пропускаются при размотке.

        aspect_name:
            Строковое имя метода-аспекта (например, "process_payment_aspect").
            Используется для диагностики, логирования и событий плагинов
            (SagaRollbackStartedEvent.aspect_names, CompensateFailedEvent.failed_for_aspect).

        state_before:
            Состояние конвейера ДО выполнения этого аспекта.
            Frozen-экземпляр BaseState. Компенсатор использует его
            для восстановления предыдущего значения.

        state_after:
            Состояние конвейера ПОСЛЕ выполнения этого аспекта.
            Frozen-экземпляр BaseState или None.
            None означает: аспект выполнился, но чекер отклонил результат —
            state не обновился, однако побочный эффект мог произойти.
            Компенсатор использует state_after для извлечения данных,
            необходимых для отката (txn_id, record_id и т.д.).
    """

    compensator: CompensatorMeta | None
    aspect_name: str
    state_before: object  # BaseState — frozen-экземпляр
    state_after: object | None  # BaseState | None — frozen-экземпляр или None
