# src/action_machine/core/saga_frame.py
"""
Фрейм стека компенсации (Saga).

Каждый успешно выполненный regular-аспект порождает один SagaFrame.
Фреймы накапливаются в локальном стеке внутри _execute_regular_aspects().
При возникновении ошибки в любом аспекте стек разматывается в обратном
порядке methodом _rollback_saga().

Архитектура:
    Фрейм хранит только данные, УНИКАЛЬНЫЕ для конкретного аспекта:
    - state_before: state до выполнения аспекта
    - state_after: state после выполнения аспекта (None если checker отклонил)
    - compensator: метаданные compensatorа (None если не определён)
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
    Поле compensator ссылается на snapshot-метаданные compensatorа.
    Если для аспекта не определён compensator, поле равно None —
    такой фрейм пропускается при размотке (счётчик skipped).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_machine.compensate.compensate_gate_host_inspector import (
        CompensateGateHostInspector,
    )


@dataclass(frozen=True)
class SagaFrame:
    """
    Один фрейм стека компенсации.

    Создаётся после успешного выполнения regular-аспекта
    (аспект вернул dict, независимо от result checkerа).

    Когда фрейм создаётся:
        - Аспект вернул dict, checkerы пройдены → state_after = новый state.
        - Аспект вернул dict, checker отклонил → state_after = None.
          Побочный эффект МОГ произойти (например, HTTP-запрос к платёжному
          шлюзу уже отправлен), поэтому фрейм создаётся для возможной
          компенсации.

    Когда фрейм НЕ создаётся:
        - Аспект бросил исключение до возврата dict.
          Побочный эффект не гарантирован, компенсировать нечего.

    Атрибуты:
        compensator:
            Метаданные compensatorа для этого аспекта.
            None — если для аспекта не определён декоратор @compensate.
            Фреймы без compensatorа пропускаются при размотке.

        aspect_name:
            Строковое имя methodа-аспекта (например, "process_payment_aspect").
            Используется для диагностики, логирования и событий плагинов
            (SagaRollbackStartedEvent.aspect_names, CompensateFailedEvent.failed_for_aspect).

        state_before:
            Состояние конвейера ДО выполнения этого аспекта.
            Frozen-экземпляр BaseState. Компенсатор использует его
            для восстановления предыдущего значения.

        state_after:
            Состояние конвейера ПОСЛЕ выполнения этого аспекта.
            Frozen-экземпляр BaseState или None.
            None означает: аспект выполнился, но checker отклонил результат —
            state не обновился, однако побочный эффект мог произойти.
            Компенсатор использует state_after для извлечения данных,
            необходимых для отката (txn_id, record_id и т.д.).
    """

    compensator: CompensateGateHostInspector.Snapshot.Compensator | None

    compensator: CompensateGateHostInspector.Snapshot.Compensator | None
    aspect_name: str
    state_before: object  # BaseState — frozen-экземпляр
    state_after: object | None  # BaseState | None — frozen-экземпляр или None
