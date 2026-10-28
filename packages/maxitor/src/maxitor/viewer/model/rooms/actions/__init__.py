# packages/maxitor/src/maxitor/viewer/model/rooms/actions/__init__.py
"""
Maxitor rooms — the actions a room connection runs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One action per operation of the room protocol (contracts/room-protocol.md), plus the
two the registry's timers run.
"""

from maxitor.viewer.model.rooms.actions.disconnect_tab_action import DisconnectTabAction
from maxitor.viewer.model.rooms.actions.end_room_action import EndRoomAction
from maxitor.viewer.model.rooms.actions.expire_participant_action import ExpireParticipantAction
from maxitor.viewer.model.rooms.actions.follow_action import FollowAction
from maxitor.viewer.model.rooms.actions.join_room_action import JoinRoomAction
from maxitor.viewer.model.rooms.actions.leave_room_action import LeaveRoomAction
from maxitor.viewer.model.rooms.actions.reload_source_for_room_action import ReloadSourceForRoomAction
from maxitor.viewer.model.rooms.actions.rename_participant_action import RenameParticipantAction
from maxitor.viewer.model.rooms.actions.report_page_action import ReportPageAction
from maxitor.viewer.model.rooms.actions.seed_page_settings_action import SeedPageSettingsAction
from maxitor.viewer.model.rooms.actions.set_page_setting_action import SetPageSettingAction
from maxitor.viewer.model.rooms.actions.stop_following_action import StopFollowingAction

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
    "StopFollowingAction",
]
