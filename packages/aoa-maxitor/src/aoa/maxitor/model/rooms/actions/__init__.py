# packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/__init__.py
"""
Maxitor rooms — the actions a room connection runs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One action per operation of the room protocol (contracts/room-protocol.md), plus the
two the registry's timers run.
"""

from aoa.maxitor.model.rooms.actions.disconnect_tab_action import DisconnectTabAction
from aoa.maxitor.model.rooms.actions.end_room_action import EndRoomAction
from aoa.maxitor.model.rooms.actions.expire_participant_action import ExpireParticipantAction
from aoa.maxitor.model.rooms.actions.follow_action import FollowAction
from aoa.maxitor.model.rooms.actions.join_room_action import JoinRoomAction
from aoa.maxitor.model.rooms.actions.leave_room_action import LeaveRoomAction
from aoa.maxitor.model.rooms.actions.reload_source_for_room_action import ReloadSourceForRoomAction
from aoa.maxitor.model.rooms.actions.rename_participant_action import RenameParticipantAction
from aoa.maxitor.model.rooms.actions.report_page_action import ReportPageAction
from aoa.maxitor.model.rooms.actions.set_page_setting_action import SetPageSettingAction
from aoa.maxitor.model.rooms.actions.stop_following_action import StopFollowingAction

__all__ = [
    "DisconnectTabAction",
    "EndRoomAction",
    "ExpireParticipantAction",
    "FollowAction",
    "JoinRoomAction",
    "LeaveRoomAction",
    "ReloadSourceForRoomAction",
    "RenameParticipantAction",
    "ReportPageAction",
    "SetPageSettingAction",
    "StopFollowingAction",
]
