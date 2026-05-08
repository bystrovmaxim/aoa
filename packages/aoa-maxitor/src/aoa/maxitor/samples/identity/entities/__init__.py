# packages/aoa-maxitor/src/aoa/maxitor/samples/identity/entities/__init__.py
from __future__ import annotations

from aoa.maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from aoa.maxitor.samples.identity.entities.identity_credential_merge import IdentityCredentialMergeCorrelateEntity
from aoa.maxitor.samples.identity.entities.identity_credential_rotation_stub import IdentityCredentialRotationStubEntity
from aoa.maxitor.samples.identity.entities.identity_email_factor import IdentityEmailFactorEntity
from aoa.maxitor.samples.identity.entities.identity_federated_linkage import IdentityFederatedLinkageEntity
from aoa.maxitor.samples.identity.entities.identity_org_binding_stub import IdentityOrgBindingStubEntity
from aoa.maxitor.samples.identity.entities.identity_person_hub import IdentityPersonHubEntity
from aoa.maxitor.samples.identity.entities.identity_phone_factor import IdentityPhoneFactorEntity

__all__ = [
    "IdentityCredentialMergeCorrelateEntity",
    "IdentityCredentialRotationStubEntity",
    "IdentityDenseLifecycle",
    "IdentityEmailFactorEntity",
    "IdentityFederatedLinkageEntity",
    "IdentityOrgBindingStubEntity",
    "IdentityPersonHubEntity",
    "IdentityPhoneFactorEntity",
]
