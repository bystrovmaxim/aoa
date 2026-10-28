# packages/maxitor/tests/graph_build_metrics.py
"""
graph_build_metrics — measure what a built graph costs and how fast it answers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One run builds a graph from coordinator JSON and reports, as one JSON object:

- the memory of that built graph by ``duckdb_memory()`` tag;
- the process size gained per graph while ten graphs are held in one process;
- the median build time;
- the median time of every diagram query and of the sidebar build;
- a SHA-256 fingerprint of every answer, so two runs can prove byte equality.

Queries that take a parameter (``list-entities``, ``domain-use-case-diagram`` and
``lifecycle-finite-automaton``) run for every domain or lifecycle in the graph, and the
slowest one is reported. This is the measurement behind issue #268; it is test tooling,
not product code, and it imports nothing that ``uv sync --no-dev`` leaves out.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

Run from ``packages/maxitor``:

    python -m tests.graph_build_metrics <graph-json URL | .json | .json.gz> [--runs N]

The argument is either a service's ``graph-json`` envelope or a bare coordinator payload.
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import gzip
import hashlib
import json
import os
import resource
import statistics
import subprocess
import sys
import time
from typing import Any

import httpx
from maxitor.viewer.model.core.actions.left_sidebar_action import GetLeftMenuSidebarDataAction
from maxitor.viewer.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from maxitor.viewer.model.diagrams.actions.full_graph_action import FullGraphAction
from maxitor.viewer.model.diagrams.actions.get_lifecycle_finite_automaton_action import (
    GetLifecycleFiniteAutomatonAction,
)
from maxitor.viewer.model.diagrams.actions.list_domains_action import ListDomainsAction
from maxitor.viewer.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.viewer.model.diagrams.actions.list_node_types_action import ListNodeTypesAction
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from tests.payload_wire_metrics import interchange_json_bytes

_MIB = 1024 * 1024
_DEFAULT_RUNS = 21
_DEFAULT_WARMUPS = 3
_DEFAULT_BUILD_RUNS = 7
_DEFAULT_RSS_COUNT = 10


def _read_ref(ref: str) -> bytes:
    """Return the uncompressed bytes of a URL, a JSON file or a gzip-compressed JSON file."""
    if ref.startswith(("http://", "https://")):
        response = httpx.get(ref, timeout=30.0)
        response.raise_for_status()
        return response.content
    if ref.endswith(".gz"):
        with gzip.open(ref, "rb") as handle:
            return handle.read()
    with open(ref, "rb") as handle:
        return handle.read()


def _decode(raw: bytes) -> dict[str, Any]:
    """Return a bare coordinator payload from raw bytes, unwrapping a ``graph-json`` envelope."""
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise TypeError("The graph source must be a JSON object")
    coordinator = parsed.get("coordinator_json")
    if isinstance(coordinator, str):
        parsed = json.loads(coordinator)
    if not isinstance(parsed, dict):
        raise TypeError("The coordinator payload must be a JSON object")
    return parsed


def load_payload(ref: str) -> dict[str, Any]:
    """Return the coordinator payload of a URL, a JSON file or a gzip-compressed JSON file."""
    return _decode(_read_ref(ref))


def memory_by_tag(resource: DuckDBGraphResource) -> dict[str, float]:
    """Return the built graph's memory in MiB per non-zero ``duckdb_memory()`` tag, plus ``total``."""
    rows = resource.execute_fetch_dicts(
        "SELECT tag, memory_usage_bytes FROM duckdb_memory() WHERE memory_usage_bytes > 0",
    )
    memory = {str(row["tag"]): int(row["memory_usage_bytes"]) / _MIB for row in rows}
    result = {tag: round(mib, 2) for tag, mib in memory.items()}
    result["total"] = round(sum(memory.values()), 2)
    return result


def _rss_mib() -> tuple[str, float]:
    """Return the process size in MiB and how it was read."""
    if sys.platform.startswith("linux"):
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return "proc/self/status", int(line.split()[1]) / 1024
        raise RuntimeError("VmRSS is missing from /proc/self/status")
    try:
        output = subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())], text=True)
    except OSError:
        try:
            import psutil
        except ImportError:
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return "getrusage-peak", peak / (_MIB if sys.platform == "darwin" else 1024)
        return "psutil", psutil.Process().memory_info().rss / _MIB
    return "ps", float(output.strip()) / 1024


def rss_per_graph(payload: dict[str, Any], count: int = _DEFAULT_RSS_COUNT) -> dict[str, Any]:
    """Return how many MiB the process gains per graph while ``count`` graphs are held."""
    gc.collect()
    method, before = _rss_mib()
    held = [DuckDBGraphResource.build_from_json(payload) for _ in range(count)]
    _, after = _rss_mib()
    del held
    gc.collect()
    return {
        "method": method,
        "before": round(before, 1),
        f"after_{count}": round(after, 1),
        "per_graph": round((after - before) / count, 1),
    }


def _apply_setting(resource: DuckDBGraphResource, setting: str) -> None:
    """Apply one ``name=value`` DuckDB setting to a built graph's connection."""
    name, _, value = setting.partition("=")
    if not name.strip() or not value.strip():
        raise ValueError(f"Expected name=value, got {setting!r}")
    resource.service.execute(f"SET {name.strip()} = {value.strip()}")


def rss_sequence(payload: dict[str, Any], setting: str | None = None) -> list[dict[str, Any]]:
    """Return the process size at each step of the issue's held-and-dropped sequence."""
    gc.collect()
    steps: list[dict[str, Any]] = []

    def record(label: str) -> None:
        _, rss = _rss_mib()
        steps.append({"step": label, "rss": round(rss, 1)})

    held: list[DuckDBGraphResource] = []
    record("0 held")
    for target in (1, 5, 10):
        while len(held) < target:
            resource = DuckDBGraphResource.build_from_json(payload)
            if setting:
                _apply_setting(resource, setting)
            held.append(resource)
        record(f"{target} held")
    held.clear()
    gc.collect()
    record("all dropped")
    again = [DuckDBGraphResource.build_from_json(payload) for _ in range(3)]
    for resource in again:
        if setting:
            _apply_setting(resource, setting)
    record("3 built again")
    return steps


def build_time_ms(payload: dict[str, Any], runs: int = _DEFAULT_BUILD_RUNS) -> float:
    """Return the median time of building the graph from the payload, in milliseconds."""
    samples: list[float] = []
    for _ in range(runs):
        started = time.perf_counter()
        DuckDBGraphResource.build_from_json(payload)
        samples.append((time.perf_counter() - started) * 1000)
    return round(statistics.median(samples), 1)


def _query_cases(resource: DuckDBGraphResource) -> list[tuple[str, type, Any]]:
    """Return ``(key, action class, params)`` for every diagram query and the sidebar build."""
    domains = [str(row["id"]) for row in resource.execute_fetch_dicts("SELECT id FROM domain ORDER BY id")]
    lifecycles = [str(row["id"]) for row in resource.execute_fetch_dicts("SELECT id FROM lifecycle ORDER BY id")]
    cases: list[tuple[str, type, Any]] = [
        ("list-domains", ListDomainsAction, ParamsStub()),
        ("list-node-types", ListNodeTypesAction, ParamsStub()),
        ("full-graph", FullGraphAction, ParamsStub()),
        ("sidebar", GetLeftMenuSidebarDataAction, ParamsStub()),
    ]
    cases.extend(
        (
            f"list-entities:{domain}",
            ListEntitiesAction,
            ListEntitiesAction.Params(domain_qualnames=[domain]),
        )
        for domain in domains
    )
    cases.extend(
        (
            f"domain-use-case-diagram:{domain}",
            GetDomainUseCaseDiagramAction,
            GetDomainUseCaseDiagramAction.Params(domain_id=domain),
        )
        for domain in domains
    )
    cases.extend(
        (
            f"lifecycle-finite-automaton:{lifecycle}",
            GetLifecycleFiniteAutomatonAction,
            GetLifecycleFiniteAutomatonAction.Params(lifecycle_graph_node_id=lifecycle),
        )
        for lifecycle in lifecycles
    )
    return cases


def _run_action(
    machine: ActionProductMachine,
    resource: DuckDBGraphResource,
    action_cls: type,
    params: Any,
) -> Any:
    """Return what the action machine answers for one action against the built graph."""

    async def run() -> Any:
        return await machine.run(
            Context(),
            action_cls(),
            params,
            connections={DUCKDB_GRAPH_CONNECTION_KEY: resource},
        )

    return asyncio.run(run())


def query_medians(
    resource: DuckDBGraphResource,
    runs: int = _DEFAULT_RUNS,
    warmups: int = _DEFAULT_WARMUPS,
) -> dict[str, float]:
    """Return the slowest median per query family, in milliseconds."""
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    medians: dict[str, float] = {}
    for key, action_cls, params in _query_cases(resource):
        for _ in range(warmups):
            _run_action(machine, resource, action_cls, params)
        samples: list[float] = []
        for _ in range(runs):
            started = time.perf_counter()
            _run_action(machine, resource, action_cls, params)
            samples.append((time.perf_counter() - started) * 1000)
        family = key.split(":", 1)[0]
        medians[family] = max(medians.get(family, 0.0), statistics.median(samples))
    return {family: round(value, 2) for family, value in medians.items()}


def fingerprints(resource: DuckDBGraphResource) -> dict[str, str]:
    """Return the SHA-256 of each answer's canonical JSON, keyed as in ``query_medians``."""
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    result: dict[str, str] = {}
    for key, action_cls, params in _query_cases(resource):
        answer = _run_action(machine, resource, action_cls, params)
        payload = json.loads(answer.model_dump_json())
        result[key] = hashlib.sha256(interchange_json_bytes(payload)).hexdigest()
    return result


class _RecordingConnection:
    """DuckDB connection proxy that records the SELECT statements the actions run."""

    def __init__(self, inner: Any, log: list[tuple[str, tuple[Any, ...]]]) -> None:
        self._inner = inner
        self._log = log

    def execute(self, sql: Any, parameters: Any = None) -> Any:
        """Record a SELECT or WITH statement, then run it on the wrapped connection."""
        if isinstance(sql, str) and sql.lstrip().upper().startswith(("SELECT", "WITH")):
            self._log.append((sql, tuple(parameters or ())))
        return self._inner.execute(sql, parameters)

    def __getattr__(self, name: str) -> Any:
        """Forward every other attribute to the wrapped connection."""
        return getattr(self._inner, name)


def _sql_literal(value: Any) -> str:
    """Return a DuckDB SQL literal for one query parameter."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _inline_parameters(sql: str, parameters: tuple[Any, ...]) -> str:
    """Return ``sql`` with every ``?`` replaced by its literal parameter value."""
    if not parameters:
        return sql
    parts = sql.split("?")
    if len(parts) != len(parameters) + 1:
        raise ValueError(f"Statement has {len(parts) - 1} placeholders but {len(parameters)} parameters")
    chunks = [parts[0]]
    for value, tail in zip(parameters, parts[1:], strict=True):
        chunks.extend((_sql_literal(value), tail))
    return "".join(chunks)


def _recorded_statements(resource: DuckDBGraphResource) -> list[tuple[str, str, tuple[Any, ...]]]:
    """Return ``(query family, SQL, parameters)`` for every statement the seven actions run."""
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    inner = resource._service
    statements: list[tuple[str, str, tuple[Any, ...]]] = []
    for key, action_cls, params in _query_cases(resource):
        log: list[tuple[str, tuple[Any, ...]]] = []
        resource._service = _RecordingConnection(inner, log)  # type: ignore[assignment]
        try:
            _run_action(machine, resource, action_cls, params)
        finally:
            resource._service = inner  # type: ignore[assignment]
        family = key.split(":", 1)[0]
        statements.extend((family, sql, values) for sql, values in log)
    return statements


def _operator_names(plan: Any) -> list[str]:
    """Return every physical operator name in an EXPLAIN plan."""
    if isinstance(plan, dict):
        own = [str(plan["name"])] if "name" in plan else []
        return own + [name for child in plan.get("children", []) for name in _operator_names(child)]
    if isinstance(plan, list):
        return [name for child in plan for name in _operator_names(child)]
    return []


def _structures_in_plan(plan: Any, names: set[str]) -> set[str]:
    """Return every catalogue structure whose name appears anywhere in the plan."""
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            found.update(name for name in names if name in value)

    walk(plan)
    return found


def _explain_plan(resource: DuckDBGraphResource, sql: str, parameters: tuple[Any, ...]) -> Any:
    """Return the JSON physical plan of ``sql`` executed with its parameter values."""
    rows = resource.execute_fetch_dicts("EXPLAIN (FORMAT JSON) " + _inline_parameters(sql, parameters))
    return json.loads(rows[0]["explain_value"])


def index_usage(resource: DuckDBGraphResource) -> dict[str, list[str]]:
    """Return, for every index and primary key, the query families whose plan reads through it."""
    indexes = resource.execute_fetch_dicts("SELECT index_name FROM duckdb_indexes() ORDER BY index_name")
    keys = resource.execute_fetch_dicts(
        "SELECT constraint_name FROM duckdb_constraints() WHERE constraint_type = 'PRIMARY KEY' "
        "ORDER BY constraint_name",
    )
    names = {str(row["index_name"]) for row in indexes} | {str(row["constraint_name"]) for row in keys}
    usage: dict[str, set[str]] = {name: set() for name in names}
    by_signature: dict[tuple[str, tuple[Any, ...]], set[str]] = {}
    for family, sql, parameters in _recorded_statements(resource):
        by_signature.setdefault((sql, parameters), set()).add(family)
    for (sql, parameters), families in by_signature.items():
        plan = _explain_plan(resource, sql, parameters)
        matched = _structures_in_plan(plan, names)
        operators = _operator_names(plan)
        if any("INDEX" in operator for operator in operators) and not matched:
            raise RuntimeError(f"An index scan names no known structure: {operators}")
        for name in matched:
            usage[name].update(families)
    return {name: sorted(families) for name, families in sorted(usage.items())}


def measure(
    ref: str,
    runs: int = _DEFAULT_RUNS,
    rss_count: int = _DEFAULT_RSS_COUNT,
    explain: bool = False,
    sequence: bool = False,
    setting: str | None = None,
) -> dict[str, Any]:
    """Return one measurement report for the graph at ``ref``."""
    raw = _read_ref(ref)
    payload = _decode(raw)
    if sequence:
        sequence_steps = rss_sequence(payload, setting)
    rss = rss_per_graph(payload, rss_count)
    resource = DuckDBGraphResource.build_from_json(payload)
    report: dict[str, Any] = {
        "source": {
            "ref": ref,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "nodes": len(payload.get("nodes", [])),
            "edges": len(payload.get("edges", [])),
        },
        "memory_mib": memory_by_tag(resource),
        "rss_per_graph_mib": rss,
        "build_ms": build_time_ms(payload),
        "query_ms": query_medians(resource, runs),
        "fingerprints": fingerprints(resource),
    }
    if explain:
        report["index_usage"] = index_usage(resource)
    if sequence:
        report["rss_mib"] = sequence_steps
    return report


def main(argv: list[str] | None = None) -> int:
    """Run the measurement over one graph and print its JSON report."""
    parser = argparse.ArgumentParser(description="Measure what a built graph costs and how fast it answers.")
    parser.add_argument("ref", help="graph-json URL, .json file or .json.gz file")
    parser.add_argument("--runs", type=int, default=_DEFAULT_RUNS, help="timed runs per query")
    parser.add_argument("--rss-count", type=int, default=_DEFAULT_RSS_COUNT, help="graphs held for the RSS figure")
    parser.add_argument("--explain", action="store_true", help="add the index usage table")
    parser.add_argument("--rss-sequence", action="store_true", help="add the issue's held-and-dropped RSS sequence")
    parser.add_argument("--setting", metavar="NAME=VALUE", help="DuckDB setting applied to every built connection")
    args = parser.parse_args(argv)
    report = measure(args.ref, args.runs, args.rss_count, args.explain, args.rss_sequence, args.setting)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
