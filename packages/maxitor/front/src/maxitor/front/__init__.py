# packages/maxitor/front/src/maxitor/front/__init__.py
"""
Maxitor — graph visualization and sidebar helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a FastAPI-backed React SPA (see :mod:`maxitor.front.api.app`) and
diagram action helpers that read an AOA service graph loaded via
:class:`~maxitor.front.model.core.actions.load_aoa_service_action.LoadAOAServiceAction`.

═══════════════════════════════════════════════════════════════════════════════
REACT SPA + FASTAPI
═══════════════════════════════════════════════════════════════════════════════

Run the backend with ``uv run task maxitor`` and the frontend with ``npm run dev``
from ``packages/maxitor/front/client``. Interchange and ERD viewers render in the SPA
from JSON under ``/api/v1`` (see ``maxitor.front.api.app``).

Set ``AOA_SERVICE_URL`` to point at a running AOA service
(default: ``http://127.0.0.1:8001``).
"""
