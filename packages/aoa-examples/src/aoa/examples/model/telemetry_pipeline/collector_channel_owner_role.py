# packages/aoa-examples/src/aoa/examples/model/telemetry_pipeline/collector_channel_owner_role.py
"""CollectorChannelOwnerRole — ingestion channel SLA owner."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class CollectorChannelOwnerRole(ApplicationRole, ABC):
    name = "telemetry_collector_channel_owner"
    description = "Ensures ingestion buffers stay within charter budget"
