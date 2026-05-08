# src/maxitor/test_domain/resources.py
"""
Runnable stub: prints the test-domain resource manager class used with ``@depends`` / ``@connection``.

Usage (from repo root, venv active)::

    python src/maxitor/test_domain/resources.py

``tests`` is not on ``PYTHONPATH`` when the file is run directly, so we prepend
the repository root (three levels above this file).
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Runtime-only import after ``sys.path`` fix; tests/ is not a package on PYTHONPATH in CI for pylint.
    from tests.scenarios.domain_model.test_db_manager import (  # pylint: disable=import-error,import-outside-toplevel
        OrdersDbManager,
    )

    print("Resource manager class for scenarios:", OrdersDbManager.__qualname__)
    print("Module:", OrdersDbManager.__module__)
    print("Example: @depends(OrdersDbManager)  @connection(OrdersDbManager, key=\"db\")")


if __name__ == "__main__":
    main()
