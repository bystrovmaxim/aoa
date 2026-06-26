# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/correlation_lane_owner_role.py
"""CorrelationLaneOwnerRole — tracer/correlation graph ownership."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.demo.model.telemetry_pipeline.normalization_lane_owner_role import NormalizationLaneOwnerRole


@role_mode(RoleMode.ALIVE)
class CorrelationLaneOwnerRole(NormalizationLaneOwnerRole, ABC):
    name = "telemetry_correlation_lane_owner"
    description = "Authorises causal stitching across edge → core spans"
