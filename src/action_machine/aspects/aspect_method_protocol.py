# src/action_machine/aspects/aspect_gate.py

from typing import Protocol, Any

class AspectMethodProtocol(Protocol):
    """
    Протокол для метода‑аспекта.

    Определяет, что метод должен быть асинхронным и принимать произвольные
    аргументы, возвращая любое значение. В будущем может быть уточнён
    под конкретную сигнатуру аспектов (params, state, deps, connections, log).
    """
    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...