# tests/__init__.py
"""Repo-root cross-package test tree.

After the #82 per-package test distribution, this root package holds only the
cross-cutting suites that span packages — currently ``tests/packaging`` (wheel
install/import smoke checks). Each package's own unit tests live under
``packages/<pkg>/tests/``.
"""
