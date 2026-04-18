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

    from tests.scenarios.domain_model.test_db_manager import TestDbManager

    print("Resource manager class for scenarios:", TestDbManager.__qualname__)
    print("Module:", TestDbManager.__module__)
    print("Example: @depends(TestDbManager)  @connection(TestDbManager, key=\"db\")")


if __name__ == "__main__":
    main()
