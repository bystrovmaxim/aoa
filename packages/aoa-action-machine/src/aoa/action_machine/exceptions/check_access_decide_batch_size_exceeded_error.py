# packages/aoa-action-machine/src/aoa/action_machine/exceptions/check_access_decide_batch_size_exceeded_error.py
"""
``CheckAccessDecideBatchSizeExceededError`` — ``machine.check_access_decide`` list larger than the configured cap.

Each item in the list form of ``check_access_decide`` triggers a real ``access_decide`` call —
typically a data lookup (e.g. a database read). Without a cap, one call could force the
machine to perform an unbounded number of such lookups in a single request.
``ActionProductMachine`` rejects an oversized list before touching any item — no partial
processing, no ``access_decide`` call for anything in the list.
"""

from __future__ import annotations


class CheckAccessDecideBatchSizeExceededError(ValueError):
    """
    Raised by ``machine.check_access_decide`` (list form) when ``len(items) > max_check_access_decide_batch_size``.

    Attributes:
        item_count: Size of the rejected batch.
        max_check_access_decide_batch_size: The configured cap (``ActionProductMachine.__init__``).
    """

    def __init__(
        self,
        message: str,
        *,
        item_count: int,
        max_check_access_decide_batch_size: int,
    ) -> None:
        super().__init__(message)
        self.item_count = item_count
        self.max_check_access_decide_batch_size = max_check_access_decide_batch_size
