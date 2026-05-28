# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/exceptions/ocel_resource_access_prohibited_error.py
"""OcelResourceAccessProhibitedError — lifecycle call from proxy connection."""

from aoa.action_machine.plugin.ocel.exceptions.ocel_error import OcelError


class OcelResourceAccessProhibitedError(OcelError):
    """Raised when action code calls ``open()`` or ``close()`` on a proxy connection.

    Not a subclass of ``OcelContractError`` — lifecycle access violation, not data contract.
    """
