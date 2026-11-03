# packages/aoa-demo/src/aoa/demo/model/catalog/review_moderator_role.py
"""ReviewModeratorRole — publishes and hides product reviews."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class ReviewModeratorRole(ApplicationRole, ABC):
    name = "catalog_review_moderator"
    description = "Publishes product reviews and hides the ones that break the rules"
