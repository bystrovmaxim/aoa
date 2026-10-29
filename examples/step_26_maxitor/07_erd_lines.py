"""
07_erd_lines.py — every line between two tables on the ERD, one per association, read the ERD way

``GET /api/v1/list-entities`` answers, per requested domain, the tables of that domain (plus its
1-hop neighbours) and the lines between them; and, for the whole request, one ``relations`` list
over all its slices. A line is drawn whenever both its tables are on screen, whatever brought each
there. A relation field and its declared inverse are one association: one row, naming the field on
each side (``source_field`` / ``target_field``) and the cardinality of each end.

The cases, with the real output at the bottom:

  1. a 1-hop slice: two neighbours of the domain are joined, as one association with two roles;
  2. a relation without an inverse is its own line, with one role;
  3. a specialization head is joined to the dictionary its axis is classified by;
  4. an extension keeps its generalization line to its head; the line names the two fields that join
     them — the extension's reverse field and the head's axis — and ends the ERD way, zero or one at
     the extension and exactly one at the head (spec 029);
  5. two domains in one request: a line whose ends come from two different slices exists only in
     the request-wide list;
  6. 1-hop decides which extra tables come in, never which fields a table lists: with 1-hop off a
     table still lists every relation field, while the lines to tables off the diagram wait;
  7. a relation that may hold nothing ends in zero or one, a mandatory one in exactly one.

Output:

    1. Events with 1-hop: the neighbours Player and Showcase are joined
       Player [zero_many] players —— showcase [one] Showcase
    2. A relation without an inverse
       Offer [zero_many] —— player [one] Player
    3. The specialization head and its axis dictionary
       UserEvent [zero_many] —— kind [one] EventKind
    4. A generalization, read like any other line
       generalization: LoginSpec [zero_one] kind —— user_event [one] UserEvent
    5. Players + Showcases: the cross-slice line
       in the Players slice: False, in the Showcases slice: False, in the request list: True
       Offer [zero_many] —— industry [one] Industry
    6. Events with 1-hop off: UserEvent still lists every field
       tables: ['EventKind', 'LoginSpec', 'ProfileSpec', 'UserEvent']
       UserEvent fields: ['kind', 'player', 'referrer', 'showcase']
       a line to Player: False
    7. A relation that may hold nothing
       UserEvent [zero_many] —— referrer [zero_one] Player

Run: uv run python examples/step_26_maxitor/07_erd_lines.py
"""

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from maxitor.front.api.app import create_app
from maxitor.front.api.graph_store import GraphEntry, GraphStore
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SOURCE = "https://game.example/graph-json"
_EMPTY_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])
_DOMAINS = {"events": "game.EventsDomain", "players": "game.PlayersDomain", "showcases": "game.ShowcasesDomain", "offers": "game.OffersDomain"}
_TABLES = {
    "UserEvent": ("events", "core"), "EventKind": ("events", "enum"), "LoginSpec": ("events", "spec"), "ProfileSpec": ("events", "spec"),
    "Player": ("players", "core"), "Showcase": ("showcases", "core"), "Industry": ("offers", "enum"), "Offer": ("offers", "core"),
}


def _id(table: str) -> str:
    """The interchange id of a table of this example."""
    return f"game.{table}Entity"


def _edge(source: str, target: str, kind: str, **properties: Any) -> dict[str, Any]:
    """One graph edge between two tables (or a table and its domain)."""
    return {"source_id": source, "target_id": target, "type": kind, "relationship": "Association", "is_dag": False, "properties": properties}


def _relation(source: str, field: str, cardinality: str, target: str, inverse: str | None = None, *, optional: bool = False) -> dict[str, Any]:
    """A relation field, with its declared inverse when it has one; ``optional`` when it may hold nothing."""
    extra: dict[str, Any] = {"inverse_entity_id": _id(target), "inverse_field": inverse} if inverse else {}
    extra["optional"] = optional
    return _edge(_id(source), _id(target), "entity_relation", field_name=field, cardinality=cardinality, relation_type="association",
                 description="", has_inverse=inverse is not None, deprecated=False, **extra)


def _graph() -> dict[str, Any]:
    """The example's graph: four domains, paired and unpaired relations, a specialization axis."""
    nodes = [{"id": q, "type": "Domain", "label": q.rsplit(".", 1)[-1], "properties": {"name": key, "description": ""}} for key, q in _DOMAINS.items()]
    nodes += [{"id": _id(t), "type": "Entity", "label": t, "properties": {"description": "", "entity_kind": kind}} for t, (_, kind) in _TABLES.items()]
    edges = [_edge(_id(t), _DOMAINS[d], "domain") for t, (d, _) in _TABLES.items()]
    edges += [
        _relation("UserEvent", "player", "one", "Player", "events"), _relation("Player", "events", "many", "UserEvent", "player"),
        _relation("UserEvent", "showcase", "one", "Showcase", "events"), _relation("Showcase", "events", "many", "UserEvent", "showcase"),
        _relation("Player", "showcase", "one", "Showcase", "players"), _relation("Showcase", "players", "many", "Player", "showcase"),
        _relation("Offer", "player", "one", "Player"),
        _relation("Offer", "industry", "one", "Industry"),
        _relation("Showcase", "industry", "one", "Industry"),
        _relation("UserEvent", "referrer", "one", "Player", optional=True),
    ]
    members = ["LoginSpec", "ProfileSpec"]
    for index, member in enumerate(members):
        edges.append(_edge(_id("UserEvent"), _id(member), "entity_specialization", field_name="kind", classifier_field=None,
                           dictionary_qualname=_id("EventKind"), dictionary_label="EventKindEntity", classifier_value=member.lower(),
                           alternative_index=index, alternatives=[f"{m.lower()} -> {_id(m)}" for m in members],
                           labels=[f"{m} ({m.lower()})" for m in members], relation_type="association", cardinality="one",
                           description="", has_inverse=False, deprecated=False))
        edges.append(_edge(_id(member), _id("UserEvent"), "parent_entity", field_name="user_event", inverse_field="kind",
                           classifier_value=member.lower(), head_entity_id=_id("UserEvent")))
    return {"schema_version": "1.0", "nodes": nodes, "edges": edges}


async def _builder(source: str) -> GraphEntry:
    """Build the one graph this example serves."""
    return GraphEntry(source=source, graph=DuckDBGraphResource.build_from_json(_graph()), sidebar=_EMPTY_SIDEBAR, last_read=0.0)


app = create_app()
app.state.graph_store = GraphStore(_builder)
client = TestClient(app, raise_server_exceptions=False)


def _read(*domains: str, one_hop: bool = True) -> dict[str, Any]:
    """``GET /api/v1/list-entities`` for the named domains, with 1-hop neighbours unless switched off."""
    params: list[tuple[str, str]] = [("source", _SOURCE), ("include_one_hop_neighbors", str(one_hop).lower())]
    params += [("domain_qualnames", _DOMAINS[d]) for d in domains]
    return client.get("/api/v1/list-entities", params=params).json()


def _short(identifier: str) -> str:
    """The table name of an id."""
    return identifier.removeprefix("game.").removesuffix("Entity")


def _line(row: dict[str, Any]) -> str:
    """A relation row the way the ERD draws it: each end's cardinality and role."""
    tail = f"{row['target_field']} " if row.get("target_field") else ""
    return f"{_short(row['source'])} [{row['source_cardinality']}] {tail}—— {row['source_field']} [{row['target_cardinality']}] {_short(row['target'])}"


def _find(rows: list[dict[str, Any]], source: str, target: str) -> dict[str, Any] | None:
    """The row from ``source`` to ``target``, if the list has one."""
    return next((r for r in rows if _short(r["source"]) == source and _short(r["target"]) == target), None)


print("1. Events with 1-hop: the neighbours Player and Showcase are joined")
events = _read("events")["domain_slices"][0]["list_entities"]["relations"]
print("  ", _line(_find(events, "Player", "Showcase")))

print("2. A relation without an inverse")
players_alone = _read("players")["domain_slices"][0]["list_entities"]["relations"]
print("  ", _line(_find(players_alone, "Offer", "Player")))

print("3. The specialization head and its axis dictionary")
print("  ", _line(_find(events, "UserEvent", "EventKind")))

print("4. A generalization, read like any other line")
generalization = _find(events, "LoginSpec", "UserEvent")
print(f"   {generalization['relationship_kind']}: {_line(generalization)}")

print("5. Players + Showcases: the cross-slice line")
both = _read("players", "showcases")
in_slices = [_find(s["list_entities"]["relations"], "Offer", "Industry") is not None for s in both["domain_slices"]]
print(f"   in the Players slice: {in_slices[0]}, in the Showcases slice: {in_slices[1]}, in the request list: {_find(both['relations'], 'Offer', 'Industry') is not None}")
print("  ", _line(_find(both["relations"], "Offer", "Industry")))

print("6. Events with 1-hop off: UserEvent still lists every field")
alone = _read("events", one_hop=False)["domain_slices"][0]["list_entities"]
user_event = next(e for e in alone["entities"] if _short(e["id"]) == "UserEvent")
print(f"   tables: {sorted(_short(e['id']) for e in alone['entities'])}")
print(f"   UserEvent fields: {[f['name'] for f in user_event['fields']]}")
print(f"   a line to Player: {_find(alone['relations'], 'UserEvent', 'Player') is not None}")

print("7. A relation that may hold nothing")
referrer = next(r for r in events if r["source_field"] == "referrer")
print("  ", _line(referrer))
