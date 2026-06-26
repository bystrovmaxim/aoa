# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/normalization_lane_owner_role.py
"""NormalizationLaneOwnerRole — deterministic transform lane stewardship."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.demo.model.telemetry_pipeline.collector_channel_owner_role import CollectorChannelOwnerRole


@role_mode(RoleMode.ALIVE)
class NormalizationLaneOwnerRole(CollectorChannelOwnerRole, ABC):
    name = "telemetry_normalization_lane_owner"
    description = "Owns parsers that enforce taxonomy before correlation"
