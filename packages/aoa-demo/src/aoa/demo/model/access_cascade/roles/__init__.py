# packages/aoa-demo/src/aoa/demo/model/access_cascade/roles/__init__.py
"""Role fixtures for the access cascade demonstrator — three branches, one chain."""

from aoa.demo.model.access_cascade.roles.cascade_application_roles import (
    CascadeLineLeadRole,
    CascadeOfficerRole,
    CascadeStaffRole,
    CascadeTraineeRole,
)
from aoa.demo.model.access_cascade.roles.cascade_domain_roles import CascadeDomainRole, CascadeDomainSpecialistRole
from aoa.demo.model.access_cascade.roles.cascade_system_role import CascadeSystemGateRole

__all__ = [
    "CascadeDomainRole",
    "CascadeDomainSpecialistRole",
    "CascadeLineLeadRole",
    "CascadeOfficerRole",
    "CascadeStaffRole",
    "CascadeSystemGateRole",
    "CascadeTraineeRole",
]
