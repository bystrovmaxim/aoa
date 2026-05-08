# tests/domain/test_domain_class_naming.py
"""
Naming invariant: subclasses of ``BaseDomain`` must use the ``Domain`` class suffix.

Enforced in ``__init_subclass__``. Violations raise ``NamingSuffixError``.
"""

import pytest

from aoa.action_machine.exceptions import NamingSuffixError


class TestDomainSuffix:
    """Every class inheriting BaseDomain must end with 'Domain'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'ShippingDomain' — definition succeeds."""
        from aoa.action_machine.domain.base_domain import BaseDomain

        class ShippingDomain(BaseDomain):
            name = "shipping"
            description = "Shipping domain"

        assert ShippingDomain.__name__.endswith("Domain")

    def test_missing_suffix_raises(self) -> None:
        """Name 'Shipping' without 'Domain' suffix → NamingSuffixError."""
        from aoa.action_machine.domain.base_domain import BaseDomain

        with pytest.raises(NamingSuffixError, match="Domain"):
            class Shipping(BaseDomain):
                name = "shipping"
                description = "Shipping domain without suffix"

    def test_intermediate_without_name_still_needs_suffix(self) -> None:
        """Intermediate abstract domain without name but correct suffix → OK."""
        from aoa.action_machine.domain.base_domain import BaseDomain

        class ExternalServiceDomain(BaseDomain):
            name = "external_service"
            description = "External service"
            is_external = True

        assert ExternalServiceDomain.__name__.endswith("Domain")

    def test_intermediate_without_suffix_raises(self) -> None:
        """Intermediate abstract domain without suffix → NamingSuffixError."""
        from aoa.action_machine.domain.base_domain import BaseDomain

        with pytest.raises(NamingSuffixError, match="Domain"):
            class ExternalService(BaseDomain):
                description = "External service without suffix"
                is_external = True
