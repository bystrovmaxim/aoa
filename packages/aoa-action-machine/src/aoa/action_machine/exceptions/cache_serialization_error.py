# packages/aoa-action-machine/src/aoa/action_machine/exceptions/cache_serialization_error.py
"""
``CacheSerializationError`` — a Result the cache cannot keep, refused at the write.

The cache keeps a Result's JSON (issue #410). Before it stores anything the machine
writes the Result, reads it back with the action's Result type and compares the two by
observable state (#409). A Result that has no JSON form, whose JSON does not read
back, or that reads back as something else is refused here, naming the Result, the
field and the cause; nothing is stored. It is a :class:`CacheContractError`, so code
that handles a broken cache contract handles it too.
"""

from __future__ import annotations

from aoa.action_machine.exceptions.cache_contract_error import CacheContractError


class CacheSerializationError(CacheContractError):
    """
    AI-CORE-BEGIN
    ROLE: Refusal of a cache write whose Result does not survive its own JSON.
    CONTRACT: Message ``<Result qualname> cannot be cached: field '<name>' <reason>.``; nothing was stored.
    AI-CORE-END
    """
