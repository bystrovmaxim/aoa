# tests/conftest.py
"""
Root pytest configuration for the only cross-cutting test tree that stays at the
repo root after the #82 per-package distribution: ``tests/packaging`` (the
cross-package wheel-install smoke). Every package's own unit tests live under
``packages/<pkg>/tests/``.

Keep this module free of imports from ``aoa.*`` so collecting one root tree does
not pull in unrelated packages. Per-package fixtures live in each package's own
``packages/<pkg>/tests/support/``.
"""
import warnings

# LangGraph raises LangChainPendingDeprecationWarning at import time (before pytest
# filterwarnings from pyproject.toml take effect).  Suppress it at the Python level.
warnings.filterwarnings("ignore", module=r"langgraph\..*")
