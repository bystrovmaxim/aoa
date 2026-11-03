# packages/maxitor/maxitor-web/maxitor/web/model/rooms/__init__.py
"""
Maxitor rooms — people looking at one service together.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The rooms domain: the registry resource, the rules (follow circles, pages and their
settings), and the actions a room connection runs.
"""

from maxitor.web.model.rooms.rooms_domain import RoomsDomain

__all__ = ["RoomsDomain"]
