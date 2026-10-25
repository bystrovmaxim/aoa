"""Verify role-access guarantees with process-local adversarial mutations.
Run: .venv/bin/python docs/reports/evidence/role_access_adversarial.py
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TESTS = "packages/aoa-action-machine/tests/action_machine/"
EXAMPLES = ROOT / "examples/step_03_authorization_and_roles"


def run_pair(mutation: str, targets: list[str]) -> dict[str, object]:
    """Run a baseline and mutation against a guarantee and its allowed neighbor."""
    result: dict[str, object] = {"mutation": mutation, "targets": targets}
    for mode in ("baseline", mutation):
        run = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child", mode, *targets],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        expected = "2 passed" if mode == "baseline" else "1 failed, 1 passed"
        assert expected in run.stdout, (mode, run.stdout, run.stderr)
        assert run.returncode == (0 if mode == "baseline" else 1)
        result[mode] = run.stdout
    return result


def child(mode: str, targets: list[str]) -> None:
    """Apply a mutation in memory before collecting the selected tests."""
    import pytest  # pylint: disable=import-outside-toplevel

    if mode != "baseline":
        changes = {
            "keywords": (
                "aoa.action_machine.intents.check_roles.check_roles_decorator",
                "if unsupported:",
                "if False and unsupported:",
                "check_roles",
            ),
            "silenced": (
                "aoa.action_machine.intents.access_control.roles",
                "if RoleMode.declared_for(rt) is RoleMode.SILENCED:",
                "if False:",
                "_active_user_roles",
            ),
            "guest_alternative": (
                "aoa.action_machine.intents.access_control.roles",
                "if GuestRole in alternatives:",
                "if spec is GuestRole:",
                "RoleChecker.check",
            ),
            "object_rule": (
                "aoa.action_machine.intents.access_control.cascade",
                "if declared is None:",
                "if True:",
                "object_gate",
            ),
            "graph_conditions": (
                "aoa.action_machine.graph.edges.role_graph_edge",
                "properties={},",
                'properties={"when": None},',
                "RoleGraphEdge.__init__",
            ),
        }
        module_name, old, new, qualname = changes[mode]
        module = importlib.import_module(module_name)
        source = Path(module.__file__).read_text()
        assert source.count(old) == 1
        namespace = {"__name__": module_name}
        exec(compile(source.replace(old, new), module.__file__, "exec"), namespace)
        original = module
        replacement = namespace
        for part in qualname.split("."):
            original = getattr(original, part)
            replacement = replacement[part] if isinstance(replacement, dict) else getattr(replacement, part)
        original.__code__ = replacement.__code__
    raise SystemExit(pytest.main(["-q", "--tb=short", *targets]))


def main() -> None:
    """Confirm each broken guarantee fails while a neighboring case passes."""
    with tempfile.TemporaryDirectory(prefix="aoa-role-access-") as temporary:
        cases = Path(temporary) / "test_examples.py"
        cases.write_text(
            "import runpy\n"
            "def test_migration():\n"
            f"    runpy.run_path({str(EXAMPLES / '24_role_declarations_and_migration.py')!r}, run_name='__main__')\n"
            "def test_graph():\n"
            f"    runpy.run_path({str(EXAMPLES / '25_access_graph.py')!r}, run_name='__main__')\n"
            "def test_silenced():\n"
            f"    runpy.run_path({str(EXAMPLES / '16_silenced_role.py')!r}, run_name='__main__')\n"
            "def test_guest_object():\n"
            f"    runpy.run_path({str(EXAMPLES / '14_guest_and_any.py')!r}, run_name='__main__')\n"
        )
        roles = TESTS + "intents/access_control/test_roles.py::"
        graph = TESTS + "graph/edges/test_role_graph_edge.py::"
        results = [
            run_pair("keywords", [str(cases) + "::test_migration", str(cases) + "::test_graph"]),
            run_pair(
                "silenced",
                [str(cases) + "::test_silenced", roles + "test_admin_allowed_with_matching_role"],
            ),
            run_pair(
                "guest_alternative",
                [
                    roles + "test_guest_beside_role_allows_anonymous_caller",
                    roles + "test_ping_none_role_allows_anonymous_context",
                ],
            ),
            run_pair(
                "object_rule", [str(cases) + "::test_guest_object", roles + "test_admin_allowed_with_matching_role"]
            ),
            run_pair(
                "graph_conditions",
                [
                    graph + "test_a_bare_role_yields_one_edge_with_empty_properties",
                    roles + "test_admin_allowed_with_matching_role",
                ],
            ),
        ]
    for result in results:
        print(result["mutation"], "baseline: 2 passed; mutation: 1 failed, 1 passed")
    if "--save" in sys.argv:
        Path(__file__).with_name("role-access-mutations.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3:])
    else:
        main()
