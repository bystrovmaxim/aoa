"""Test support facade for aoa-ocel — re-exports scenario symbols.

ocel tests import scenario entities from here instead of from the cross-package
``tests.action_machine.scenarios.*`` tree.
"""

from .domain_model import SampleEntity, TestDomain

__all__ = ["SampleEntity", "TestDomain"]
