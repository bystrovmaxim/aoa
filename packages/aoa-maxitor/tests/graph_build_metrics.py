# packages/aoa-maxitor/tests/graph_build_metrics.py
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

Run from ``packages/aoa-maxitor``:

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

from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.core.actions.left_sidebar_action import GetLeftMenuSidebarDataAction
from aoa.maxitor.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from aoa.maxitor.model.diagrams.actions.full_graph_action import FullGraphAction
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import (
    GetLifecycleFiniteAutomatonAction,
)
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.actions.list_node_types_action import ListNodeTypesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)
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
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return "getrusage-peak", peak / (_MIB if sys.platform == "darwin" else 1024)
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


def measure(ref: str, runs: int = _DEFAULT_RUNS, rss_count: int = _DEFAULT_RSS_COUNT) -> dict[str, Any]:
    """Return one measurement report for the graph at ``ref``."""
    raw = _read_ref(ref)
    payload = _decode(raw)
    rss = rss_per_graph(payload, rss_count)
    resource = DuckDBGraphResource.build_from_json(payload)
    return {
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


def main(argv: list[str] | None = None) -> int:
    """Run the measurement over one graph and print its JSON report."""
    parser = argparse.ArgumentParser(description="Measure what a built graph costs and how fast it answers.")
    parser.add_argument("ref", help="graph-json URL, .json file or .json.gz file")
    parser.add_argument("--runs", type=int, default=_DEFAULT_RUNS, help="timed runs per query")
    parser.add_argument("--rss-count", type=int, default=_DEFAULT_RSS_COUNT, help="graphs held for the RSS figure")
    args = parser.parse_args(argv)
    print(json.dumps(measure(args.ref, args.runs, args.rss_count), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
