# src/maxitor/graph_export.py
"""
Экспорт ``PyDiGraph`` координатора в **GraphML** (``rustworkx.write_graphml``).

Узлы исходного графа содержат ``class_ref`` (тип Python) и прочие объекты —
``write_graphml`` их не сериализует, поэтому строится **копия** с тем же
индексом вершин в поле ``rw_index`` и только строковыми атрибутами.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import rustworkx as rx

# Рядом с ``test_domain_graph.html`` — то же базовое имя, расширение .graphml
DEFAULT_TEST_DOMAIN_GRAPH_GRAPHML = "test_domain_graph.graphml"


def _archive_logs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "archive" / "logs"


def pygraph_to_graphml_string_dicts(graph: rx.PyDiGraph) -> rx.PyDiGraph:
    """
    Копия направленного графа: те же рёбра (после отображения индексов), данные
    узла/ребра — только строки, пригодные для GraphML.

    Узел: ``name``, ``type`` (``node_type``), ``class_name``, ``graph_key``, ``rw_index``.
    Ребро: ``type`` (``edge_type``), при наличии — ``meta`` (JSON).
    """
    out = rx.PyDiGraph()
    old_to_new: dict[int, int] = {}
    for idx in graph.node_indices():
        raw = graph[idx]
        node = dict(raw) if isinstance(raw, dict) else {}
        name = str(node.get("name", "") or "")
        node_type = str(node.get("node_type", "") or "")
        cr = node.get("class_ref")
        class_name = (
            f"{cr.__module__}.{cr.__qualname__}" if isinstance(cr, type) else ""
        )
        graph_key = f"{node_type}:{name}" if node_type or name else str(int(idx))
        payload = {
            "name": name,
            "type": node_type,
            "class_name": class_name,
            "graph_key": graph_key,
            "rw_index": str(int(idx)),
        }
        old_to_new[idx] = out.add_node(payload)
    for s, t, w in graph.weighted_edge_list():
        ed = dict(w) if isinstance(w, dict) else {}
        edge_type = str(ed.get("edge_type", "") or "")
        ep: dict[str, str] = {"type": edge_type}
        meta = ed.get("meta")
        if meta is not None:
            try:
                ep["meta"] = json.dumps(meta, ensure_ascii=False, default=str)[:8000]
            except TypeError:
                ep["meta"] = str(meta)[:8000]
        out.add_edge(old_to_new[s], old_to_new[t], ep)
    return out


def export_pygraph_to_graphml(graph: rx.PyDiGraph, output_path: str | Path) -> Path:
    """
    Записать **реальную** топологию ``graph`` в GraphML (копия со строковыми полями).

    Топология 1:1 с исходным графом; порядок добавления узлов сохраняет
    соответствие ``rw_index`` ↔ исходный индекс ``PyDiGraph``.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = pygraph_to_graphml_string_dicts(graph)
    rx.write_graphml(safe, str(path))
    return path


def export_test_domain_graph_graphml(
    output_path: str | Path | None = None,
    *,
    use_timestamp: bool = False,
) -> Path:
    """
    Собрать координатор ``test_domain`` и записать GraphML в ``archive/logs``.

    По умолчанию файл ``test_domain_graph.graphml`` (как у HTML — тот же каталог
    и то же базовое имя). С ``use_timestamp=True`` — отдельный файл с UTC-меткой.
    """
    from maxitor.test_domain.build import build_test_coordinator

    coordinator = build_test_coordinator()
    graph = coordinator.get_graph()

    if output_path is not None:
        target = Path(output_path)
    else:
        log_dir = _archive_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = (
            f"test_domain_graph_{ts}.graphml"
            if use_timestamp
            else DEFAULT_TEST_DOMAIN_GRAPH_GRAPHML
        )
        target = log_dir / name

    written = export_pygraph_to_graphml(graph, target)
    print(f"Graph GraphML written to {written}")
    return written


if __name__ == "__main__":
    export_test_domain_graph_graphml()
