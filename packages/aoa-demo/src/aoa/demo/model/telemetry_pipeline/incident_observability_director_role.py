# packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/incident_observability_director_role.py
"""IncidentObservabilityDirectorRole — command authority bridging SRE overlays."""

from __future__ import annotations

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.demo.model.telemetry_pipeline.correlation_lane_owner_role import CorrelationLaneOwnerRole


@role_mode(RoleMode.ALIVE)
class IncidentObservabilityDirectorRole(CorrelationLaneOwnerRole):
    name = "telemetry_incident_observability_director"
    description = "Incident commander sign-off on ingest + correlate releases"
