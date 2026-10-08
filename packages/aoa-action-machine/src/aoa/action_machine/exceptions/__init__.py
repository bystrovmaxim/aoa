# packages/aoa-action-machine/src/aoa/action_machine/exceptions/__init__.py
"""
Framework-level exceptions for ActionMachine.

Import public types from here, for example ``from aoa.action_machine.exceptions import NamingSuffixError``.
"""

from aoa.action_machine.exceptions.access_condition_async_error import AccessConditionAsyncError
from aoa.action_machine.exceptions.action_result_declaration_error import ActionResultDeclarationError
from aoa.action_machine.exceptions.action_result_type_error import ActionResultTypeError
from aoa.action_machine.exceptions.aspect_declaration_error import AspectDeclarationError
from aoa.action_machine.exceptions.aspect_pipeline_error import AspectPipelineError
from aoa.action_machine.exceptions.async_required_error import AsyncRequiredError
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.exceptions.cache_contract_error import CacheContractError
from aoa.action_machine.exceptions.check_access_decide_batch_size_exceeded_error import (
    CheckAccessDecideBatchSizeExceededError,
)
from aoa.action_machine.exceptions.checker_declaration_error import CheckerDeclarationError
from aoa.action_machine.exceptions.condition_reason_error import ConditionReasonError
from aoa.action_machine.exceptions.connection_already_open_error import ConnectionAlreadyOpenError
from aoa.action_machine.exceptions.connection_not_open_error import ConnectionNotOpenError
from aoa.action_machine.exceptions.connection_validation_error import ConnectionValidationError
from aoa.action_machine.exceptions.context_access_error import ContextAccessError
from aoa.action_machine.exceptions.cyclic_dependency_error import CyclicDependencyError
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.decorator_argument_type_error import DecoratorArgumentTypeError
from aoa.action_machine.exceptions.decorator_argument_value_error import DecoratorArgumentValueError
from aoa.action_machine.exceptions.decorator_target_error import DecoratorTargetError
from aoa.action_machine.exceptions.dependency_declaration_error import DependencyDeclarationError
from aoa.action_machine.exceptions.description_contract_error import DescriptionContractError
from aoa.action_machine.exceptions.description_type_error import DescriptionTypeError
from aoa.action_machine.exceptions.domain_graph_edge_resolution_error import DomainGraphEdgeResolutionError
from aoa.action_machine.exceptions.duplicate_declaration_error import DuplicateDeclarationError
from aoa.action_machine.exceptions.graph_edge_resolution_error import GraphEdgeResolutionError
from aoa.action_machine.exceptions.handle_error import HandleError
from aoa.action_machine.exceptions.include_contract_violation_error import IncludeContractViolationError
from aoa.action_machine.exceptions.intent_resolution_error import IntentResolutionError
from aoa.action_machine.exceptions.log_template_error import LogTemplateError
from aoa.action_machine.exceptions.missing_check_roles_error import MissingCheckRolesError
from aoa.action_machine.exceptions.missing_declaration_error import MissingDeclarationError
from aoa.action_machine.exceptions.missing_entity_info_error import MissingEntityInfoError
from aoa.action_machine.exceptions.missing_meta_error import MissingMetaError
from aoa.action_machine.exceptions.missing_summary_aspect_error import MissingSummaryAspectError
from aoa.action_machine.exceptions.naming_prefix_error import NamingPrefixError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.exceptions.on_error_handler_error import OnErrorHandlerError
from aoa.action_machine.exceptions.params_graph_edge_resolution_error import ParamsGraphEdgeResolutionError
from aoa.action_machine.exceptions.result_graph_edge_resolution_error import ResultGraphEdgeResolutionError
from aoa.action_machine.exceptions.role_mode_declaration_error import RoleModeDeclarationError
from aoa.action_machine.exceptions.role_spec_type_error import RoleSpecTypeError
from aoa.action_machine.exceptions.rollup_not_supported_error import RollupNotSupportedError
from aoa.action_machine.exceptions.signature_contract_error import SignatureContractError
from aoa.action_machine.exceptions.transaction_error import TransactionError
from aoa.action_machine.exceptions.transaction_prohibited_error import TransactionProhibitedError
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
from aoa.action_machine.exceptions.verdict_contract_error import VerdictContractError

__all__ = [
    "AccessConditionAsyncError",
    "ActionResultDeclarationError",
    "ActionResultTypeError",
    "AspectDeclarationError",
    "AspectPipelineError",
    "AsyncRequiredError",
    "AuthorizationError",
    "CacheContractError",
    "CheckAccessDecideBatchSizeExceededError",
    "CheckerDeclarationError",
    "ConditionReasonError",
    "ConnectionAlreadyOpenError",
    "ConnectionNotOpenError",
    "ConnectionValidationError",
    "ContextAccessError",
    "CyclicDependencyError",
    "DeclarationStructureError",
    "DecoratorArgumentTypeError",
    "DecoratorArgumentValueError",
    "DecoratorTargetError",
    "DependencyDeclarationError",
    "DescriptionContractError",
    "DescriptionTypeError",
    "DomainGraphEdgeResolutionError",
    "DuplicateDeclarationError",
    "GraphEdgeResolutionError",
    "HandleError",
    "IncludeContractViolationError",
    "IntentResolutionError",
    "LogTemplateError",
    "MissingCheckRolesError",
    "MissingDeclarationError",
    "MissingEntityInfoError",
    "MissingMetaError",
    "MissingSummaryAspectError",
    "NamingPrefixError",
    "NamingSuffixError",
    "OnErrorHandlerError",
    "ParamsGraphEdgeResolutionError",
    "ResultGraphEdgeResolutionError",
    "RoleModeDeclarationError",
    "RoleSpecTypeError",
    "RollupNotSupportedError",
    "SignatureContractError",
    "TransactionError",
    "TransactionProhibitedError",
    "ValidationFieldError",
    "VerdictContractError",
]
