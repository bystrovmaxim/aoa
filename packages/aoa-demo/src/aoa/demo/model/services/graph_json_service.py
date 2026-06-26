# packages/aoa-demo/src/aoa/demo/model/services/graph_json_service.py
"""
Build and cache interchange JSON for the registered example model coordinator.
"""

from __future__ import annotations

from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator


class ExampleModelGraphJsonService:
    """
    Process-local cache for :meth:`build_registered_interchange_coordinator().to_json`.

    Coordinator construction imports many registration modules; caching keeps
    repeated HTTP probes cheap for the FastAPI example app.
    """

    _cached_json: str | None = None

    @classmethod
    def clear_cache(cls) -> None:
        """Drop cached JSON (for tests)."""
        cls._cached_json = None

    def coordinator_json(self) -> str:
        """Return interchange JSON string for the demo coordinator."""
        if self._cached_json is not None:
            return self._cached_json
        coordinator = build_registered_interchange_coordinator()
        payload = coordinator.to_json()
        type(self)._cached_json = payload
        return payload
