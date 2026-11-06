# packages/aoa-action-machine/tests/action_machine/intents/plugins/test_observer_naming.py
"""ObserverNaming — plugin and logger names are validated at declaration."""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.plugin.core import BasePlugin


@pytest.mark.parametrize("base,suffix", [(BasePlugin, "Plugin"), (BaseLogger, "Logger")])
def test_observer_names_accept_direct_and_indirect_descendants(base, suffix):
    """Permit abstract intermediate classes and correctly named descendants."""
    parent = type(f"Audit{suffix}", (base,), {})
    child = type(f"DetailedAudit{suffix}", (parent,), {})
    assert issubclass(child, base)


@pytest.mark.parametrize("base,suffix", [(BasePlugin, "Plugin"), (BaseLogger, "Logger")])
@pytest.mark.parametrize("name", ["Audit", "PluginAudit", "AuditLoggerSuffix", "Auditplugin", "Auditlogger"])
def test_observer_names_refuse_missing_or_misplaced_suffix(base, suffix, name):
    """Require the exact suffix at the end of every declared name."""
    with pytest.raises(NamingSuffixError) as caught:
        type(name, (base,), {})
    assert str(caught.value) == (
        f"Class '{name}' inherits {base.__name__} but lacks the '{suffix}' suffix. "
        f"Rename to '{name}{suffix}'."
    )


@pytest.mark.parametrize("base,suffix", [(BasePlugin, "Plugin"), (BaseLogger, "Logger")])
def test_observer_names_check_indirect_descendants(base, suffix):
    """Keep enforcement when an intermediate observer is abstract."""
    parent = type(f"Audit{suffix}", (base,), {})
    with pytest.raises(NamingSuffixError, match="Class 'DetailedAudit'"):
        type("DetailedAudit", (parent,), {})


@pytest.mark.parametrize("base,suffix", [(BasePlugin, "Plugin"), (BaseLogger, "Logger")])
def test_observer_naming_preserves_cooperative_subclass_hooks(base, suffix):
    """Forward class keywords to the next cooperative base."""
    observed = []

    class RegistrationMixin:
        """Consume an application registration keyword."""

        def __init_subclass__(cls, *, register=False, **kwargs):
            """Record registration without interfering with naming."""
            super().__init_subclass__(**kwargs)
            observed.append((cls, register))

    observer = type(f"Registered{suffix}", (base, RegistrationMixin), {}, register=True)
    assert observed == [(observer, True)]
