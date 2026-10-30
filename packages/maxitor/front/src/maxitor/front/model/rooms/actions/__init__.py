# packages/maxitor/front/src/maxitor/front/model/rooms/actions/__init__.py
"""
Maxitor rooms — the actions a room connection runs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One action per operation of the room protocol (contracts/room-protocol.md), plus the
two the registry's timers run.
"""

from maxitor.front.model.rooms.actions.disconnect_tab_action import DisconnectTabAction
from maxitor.front.model.rooms.actions.end_room_action import EndRoomAction
from maxitor.front.model.rooms.actions.expire_participant_action import ExpireParticipantAction
from maxitor.front.model.rooms.actions.follow_action import FollowAction
from maxitor.front.model.rooms.actions.join_room_action import JoinRoomAction
from maxitor.front.model.rooms.actions.leave_room_action import LeaveRoomAction
from maxitor.front.model.rooms.actions.reload_source_for_room_action import ReloadSourceForRoomAction
from maxitor.front.model.rooms.actions.rename_participant_action import RenameParticipantAction
from maxitor.front.model.rooms.actions.report_page_action import ReportPageAction
from maxitor.front.model.rooms.actions.seed_page_settings_action import SeedPageSettingsAction
from maxitor.front.model.rooms.actions.set_page_setting_action import SetPageSettingAction
from maxitor.front.model.rooms.actions.set_room_version_action import SetRoomVersionAction
from maxitor.front.model.rooms.actions.stop_following_action import StopFollowingAction

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
    "SeedPageSettingsAction",
    "SetPageSettingAction",
    "SetRoomVersionAction",
    "StopFollowingAction",
]
