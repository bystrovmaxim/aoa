# packages/aoa-demo/src/aoa/demo/model/dictionaries/domain.py
"""The domain that groups the demo's shared dictionaries."""

from __future__ import annotations

from aoa.action_machine.domain.base_domain import BaseDomain


class DictionariesDomain(BaseDomain):
    """Group the dictionaries every business domain may reference."""

    name = "dictionaries"
    description = "Shared reference dictionaries"
