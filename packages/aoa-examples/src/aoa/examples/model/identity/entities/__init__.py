# packages/aoa-examples/src/aoa/examples/model/identity/entities/__init__.py
from __future__ import annotations

from aoa.examples.model.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from aoa.examples.model.identity.entities.identity_credential_merge import IdentityCredentialMergeCorrelateEntity
from aoa.examples.model.identity.entities.identity_credential_rotation_stub import IdentityCredentialRotationStubEntity
from aoa.examples.model.identity.entities.identity_email_factor import IdentityEmailFactorEntity
from aoa.examples.model.identity.entities.identity_federated_linkage import IdentityFederatedLinkageEntity
from aoa.examples.model.identity.entities.identity_org_binding_stub import IdentityOrgBindingStubEntity
from aoa.examples.model.identity.entities.identity_person_hub import IdentityPersonHubEntity
from aoa.examples.model.identity.entities.identity_phone_factor import IdentityPhoneFactorEntity

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
