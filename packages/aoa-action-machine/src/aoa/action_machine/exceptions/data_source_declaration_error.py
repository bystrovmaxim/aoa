# packages/aoa-action-machine/src/aoa/action_machine/exceptions/data_source_declaration_error.py
"""DataSourceDeclarationError — a resource names a data source it cannot have, or is given the wrong one."""


class DataSourceDeclarationError(TypeError):
    """
    AI-CORE-BEGIN
        ROLE: Fail-fast signal for a wrong data source on a resource.
        CONTRACT: Raised when a resource class names a data source of the wrong kind or two data sources, and when a resource is built with a data source it does not declare, or without the one it does.
        INVARIANTS: The message names the resource, what it declares and what it was given.
    AI-CORE-END
    """
