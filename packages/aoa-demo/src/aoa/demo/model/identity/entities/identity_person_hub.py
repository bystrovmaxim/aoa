# packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_person_hub.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from aoa.demo.model.identity.resources.identity_store_base import IdentityStoreBase


@entity(description="Person identity hub for credentials, factors, federation, and recovery", resource=IdentityStoreBase)
class IdentityPersonHubCoreEntity(BaseCoreEntity):
    id: str = Field(description="Person id")
    lifecycle: IdentityDenseLifecycle = Field(description="Person aggregate lifecycle")

    subject_handle: str = Field(description="Pseudonymous subject moniker for federation")
    risk_band: str = Field(description="Assurance tier surfaced to policy engines")
    last_seen_ip_hash: str = Field(description="Salted client-network fingerprint heuristic")
    mfa_saturation_pct: float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)
    recovery_budget_left: int = Field(description="Remaining recovery-token attempts envelope", ge=0)
    linkage_audit_seq: int = Field(description="Monotonic merge audit ticker", ge=0)


IdentityPersonHubCoreEntity.model_rebuild()
