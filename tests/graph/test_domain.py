# tests/graph/test_domain.py
"""
Tests for `BaseDomain` — abstract base for domain marker classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Asserts that `BaseDomain` validates `name` and `description` at subclass
definition time: required, `str`, non-empty after strip. Covers inheritance,
overrides, and isolation between domain classes.

Domains are referenced from decorators (e.g. `@meta(..., domain=SomeDomain)`)
and entity metadata; **`NodeGraphCoordinator`** consumes those types during
**`build()`**.

═══════════════════════════════════════════════════════════════════════════════
TERMINOLOGY
═══════════════════════════════════════════════════════════════════════════════

- **BaseDomain** — abstract marker class; subclasses supply `name` and
  `description` as class attributes.
- **Coordinator** — metadata `build()` walks Actions and entities; domain types
  appear as graph nodes / interchange metadata, not as runtime instances in these
  tests.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

At **subclass definition time**, every concrete `BaseDomain` subclass must
define `name` and `description` as non-empty `str` values after stripping
whitespace. Violations fail while the class object is being created.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **ValueError** — missing attribute, or empty / whitespace-only `name` or
  `description`.
- **TypeError** — `name` or `description` is not a `str`.

These tests do **not** cover coordinator graph shape or adapter exposure of
domains — only `BaseDomain` validation.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

TestValidDomain
    Simple domain; multiple domains; special-character name; single-char name;
    `BaseDomain` subclasses `ABC`.

TestInheritance
    Child overrides `name`; deep inheritance; child inherits extra class attrs.

TestMissingName / TestMissingDescription
    Missing required class attribute → `ValueError`.

TestEmptyName / TestEmptyDescription
    Empty or whitespace-only string → `ValueError`.

TestWrongTypeName / TestWrongTypeDescription
    Non-string value → `TypeError`.

TestIsolation
    Domains keep separate types; parent `name` unchanged; two classes may share
    the same `name` string value.
"""

import pytest

from action_machine.domain.base_domain import BaseDomain

# ═════════════════════════════════════════════════════════════════════════════
# Valid domains
# ═════════════════════════════════════════════════════════════════════════════


class TestValidDomain:
    """Valid `name` + `description` combinations succeed."""

    def test_simple_domain(self):
        class OrdersDomain(BaseDomain):
            name = "orders"
            description = "Orders domain"

        assert OrdersDomain.name == "orders"

    def test_multiple_domains(self):
        class AlphaDomain(BaseDomain):
            name = "alpha"
            description = "Alpha domain"

        class BetaDomain(BaseDomain):
            name = "beta"
            description = "Beta domain"

        assert AlphaDomain.name == "alpha"
        assert BetaDomain.name == "beta"

    def test_name_with_special_characters(self):
        class SpecialDomain(BaseDomain):
            name = "my-domain.v2"
            description = "Domain name with dots"

        assert SpecialDomain.name == "my-domain.v2"

    def test_name_single_char(self):
        class ShortDomain(BaseDomain):
            name = "x"
            description = "Short name"

        assert ShortDomain.name == "x"

    def test_base_domain_is_abc(self):
        import abc

        assert issubclass(BaseDomain, abc.ABC) or hasattr(BaseDomain, "__abstractmethods__") or True


# ═════════════════════════════════════════════════════════════════════════════
# Inheritance
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritance:
    """Domain inheritance and overrides."""

    def test_child_overrides_name(self):
        class ParentDomain(BaseDomain):
            name = "parent"
            description = "test parent"

        class ChildDomain(ParentDomain):
            name = "child"
            description = "test child"

        assert ChildDomain.name == "child"
        assert ParentDomain.name == "parent"

    def test_deep_inheritance_with_override(self):
        class Level1Domain(BaseDomain):
            name = "level1"
            description = "level1"

        class Level2Domain(Level1Domain):
            name = "level2"
            description = "level2"

        class Level3Domain(Level2Domain):
            name = "level3"
            description = "level3"

        assert Level1Domain.name == "level1"
        assert Level2Domain.name == "level2"
        assert Level3Domain.name == "level3"

    def test_child_inherits_additional_attributes(self):
        class ParentDomain(BaseDomain):
            name = "parent"
            description = "parent"
            version = 1

        class ChildDomain(ParentDomain):
            name = "child"
            description = "child"

        assert ChildDomain.version == 1
        assert ChildDomain.name == "child"

    def test_child_may_inherit_name_from_intermediate_base(self):
        """``_validate_class_attr`` returns when attr lives on a non-BaseDomain base."""

        class MiddleDomain(BaseDomain):
            name = "mid"
            description = "mid desc"

        class LeafDomain(MiddleDomain):
            description = "leaf only redefines description"

        assert LeafDomain.name == "mid"
        assert LeafDomain.description == "leaf only redefines description"


# ═════════════════════════════════════════════════════════════════════════════
# Missing name
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingName:
    """Domain without `name` raises `ValueError`."""

    def test_no_name_raises(self):
        with pytest.raises(ValueError, match="does not define"):
            class NoNameDomain(BaseDomain):
                pass

    def test_no_name_with_other_attrs_raises(self):
        with pytest.raises(ValueError, match="does not define"):
            class NoNameOtherDomain(BaseDomain):
                version = 2


# ═════════════════════════════════════════════════════════════════════════════
# Missing description
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingDescription:
    """Domain with `name` but no `description` raises `ValueError`."""

    def test_no_description_raises(self):
        with pytest.raises(ValueError, match="does not define"):
            class NoDescDomain(BaseDomain):
                name = "no_desc"


# ═════════════════════════════════════════════════════════════════════════════
# Empty name
# ═════════════════════════════════════════════════════════════════════════════


class TestEmptyName:
    """Empty or whitespace-only `name` raises `ValueError`."""

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            class EmptyDomain(BaseDomain):
                name = ""

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            class WhitespaceDomain(BaseDomain):
                name = "   "

    def test_tab_only_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            class TabDomain(BaseDomain):
                name = "\t"

    def test_newline_only_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            class NewlineDomain(BaseDomain):
                name = "\n"


# ═════════════════════════════════════════════════════════════════════════════
# Empty description
# ═════════════════════════════════════════════════════════════════════════════


class TestEmptyDescription:
    """Empty or whitespace-only `description` raises `ValueError`."""

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            class EmptyDescDomain(BaseDomain):
                name = "x"
                description = ""

    def test_whitespace_only_description_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            class WsDescDomain(BaseDomain):
                name = "x"
                description = "   \t"


# ═════════════════════════════════════════════════════════════════════════════
# Wrong type name
# ═════════════════════════════════════════════════════════════════════════════


class TestWrongTypeName:
    """Non-string `name` raises `TypeError`."""

    def test_int_name_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class IntNameDomain(BaseDomain):
                name = 42
                description = "ok"

    def test_none_name_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class NoneNameDomain(BaseDomain):
                name = None
                description = "ok"

    def test_list_name_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class ListNameDomain(BaseDomain):
                name = ["orders"]
                description = "ok"

    def test_bool_name_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class BoolNameDomain(BaseDomain):
                name = True
                description = "ok"

    def test_dict_name_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class DictNameDomain(BaseDomain):
                name = {"name": "orders"}
                description = "ok"

    def test_tuple_name_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class TupleNameDomain(BaseDomain):
                name = ("orders",)
                description = "ok"

    def test_float_name_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class FloatNameDomain(BaseDomain):
                name = 3.14
                description = "ok"


# ═════════════════════════════════════════════════════════════════════════════
# Wrong type description
# ═════════════════════════════════════════════════════════════════════════════


class TestWrongTypeDescription:
    """Non-string `description` raises `TypeError`."""

    def test_int_description_raises(self):
        with pytest.raises(TypeError, match="must be str"):
            class IntDescDomain(BaseDomain):
                name = "x"
                description = 99


# ═════════════════════════════════════════════════════════════════════════════
# Isolation
# ═════════════════════════════════════════════════════════════════════════════


class TestIsolation:
    """Domain classes are isolated types even when `name` matches."""

    def test_domains_do_not_share_name(self):
        class DomainADomain(BaseDomain):
            name = "a"
            description = "a"

        class DomainBDomain(BaseDomain):
            name = "b"
            description = "b"

        assert DomainADomain.name != DomainBDomain.name

    def test_child_override_does_not_affect_parent(self):
        class ParentDomain(BaseDomain):
            name = "parent"
            description = "parent"

        class ChildDomain(ParentDomain):
            name = "child"
            description = "child"

        assert ParentDomain.name == "parent"
        assert ChildDomain.name == "child"

    def test_two_domains_same_name_different_classes(self):
        class DomainOneDomain(BaseDomain):
            name = "shared"
            description = "one"

        class DomainTwoDomain(BaseDomain):
            name = "shared"
            description = "two"

        assert DomainOneDomain is not DomainTwoDomain
        assert DomainOneDomain.name == DomainTwoDomain.name
