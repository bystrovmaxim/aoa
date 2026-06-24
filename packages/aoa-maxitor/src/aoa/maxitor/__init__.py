# packages/aoa-maxitor/src/aoa/maxitor/__init__.py
"""
Maxitor — graph visualization and sidebar helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a FastAPI-backed React SPA (see :mod:`aoa.maxitor.api.app`) and
diagram action helpers that read an AOA service graph loaded via
:class:`~aoa.maxitor.model.core.actions.load_aoa_service_action.LoadAOAServiceAction`.

═══════════════════════════════════════════════════════════════════════════════
REACT SPA + FASTAPI
═══════════════════════════════════════════════════════════════════════════════

Run the backend with ``uv run task maxitor-api`` and the frontend with ``npm run dev``
from ``packages/aoa-maxitor/client``. Interchange and ERD viewers render in the SPA
from JSON under ``/api/v1`` (see ``aoa.maxitor.api.app``).

Set ``AOA_SERVICE_URL`` to point at a running ``aoa-examples`` service
(default: ``http://127.0.0.1:8001``).
"""
