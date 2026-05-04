# src/action_machine/exceptions/__init__.py
"""
Framework-level exceptions for ActionMachine.

Import public types from here, for example ``from action_machine.exceptions import NamingSuffixError``.
"""

from action_machine.exceptions.action_result_declaration_error import ActionResultDeclarationError
from action_machine.exceptions.action_result_type_error import ActionResultTypeError
from action_machine.exceptions.aspect_pipeline_error import AspectPipelineError
from action_machine.exceptions.authorization_error import AuthorizationError
from action_machine.exceptions.connection_already_open_error import ConnectionAlreadyOpenError
from action_machine.exceptions.connection_not_open_error import ConnectionNotOpenError
from action_machine.exceptions.connection_validation_error import ConnectionValidationError
from action_machine.exceptions.context_access_error import ContextAccessError
from action_machine.exceptions.cyclic_dependency_error import CyclicDependencyError
from action_machine.exceptions.domain_graph_edge_resolution_error import DomainGraphEdgeResolutionError
from action_machine.exceptions.graph_edge_resolution_error import GraphEdgeResolutionError
from action_machine.exceptions.handle_error import HandleError
from action_machine.exceptions.log_template_error import LogTemplateError
from action_machine.exceptions.missing_check_roles_error import MissingCheckRolesError
from action_machine.exceptions.missing_entity_info_error import MissingEntityInfoError
from action_machine.exceptions.missing_meta_error import MissingMetaError
from action_machine.exceptions.missing_summary_aspect_error import MissingSummaryAspectError
from action_machine.exceptions.naming_prefix_error import NamingPrefixError
from action_machine.exceptions.naming_suffix_error import NamingSuffixError
from action_machine.exceptions.on_error_handler_error import OnErrorHandlerError
from action_machine.exceptions.params_graph_edge_resolution_error import ParamsGraphEdgeResolutionError
from action_machine.exceptions.result_graph_edge_resolution_error import ResultGraphEdgeResolutionError
from action_machine.exceptions.rollup_not_supported_error import RollupNotSupportedError
from action_machine.exceptions.transaction_error import TransactionError
from action_machine.exceptions.transaction_prohibited_error import TransactionProhibitedError
from action_machine.exceptions.validation_field_error import ValidationFieldError

__all__ = [
    "ActionResultDeclarationError",
    "ActionResultTypeError",
    "AspectPipelineError",
    "AuthorizationError",
    "ConnectionAlreadyOpenError",
    "ConnectionNotOpenError",
    "ConnectionValidationError",
    "ContextAccessError",
    "CyclicDependencyError",
    "DomainGraphEdgeResolutionError",
    "GraphEdgeResolutionError",
    "HandleError",
    "LogTemplateError",
    "MissingCheckRolesError",
    "MissingEntityInfoError",
    "MissingMetaError",
    "MissingSummaryAspectError",
    "NamingPrefixError",
    "NamingSuffixError",
    "OnErrorHandlerError",
    "ParamsGraphEdgeResolutionError",
    "ResultGraphEdgeResolutionError",
    "RollupNotSupportedError",
    "TransactionError",
    "TransactionProhibitedError",
    "ValidationFieldError",
]
