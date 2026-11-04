<!-- translated-from: catalog-filling.ru_draft.md @ 2026-11-04T19:50:28Z (filesystem mtime; draft is gitignored, no git history) · sha256:28ac8c4e6f1f -->
# Maxitor concept: how the catalog is filled

---

## The rule

**What has no other source is entered by hand. What the code knows is derived from the code.**

| What | Where it comes from |
|---|---|
| The list of Software Systems: digital products and external systems | by hand: they are not in the code, they are logical labels |
| Which containers a Software System holds | by hand |
| A container | by hand, and it gets its link right away |
| Our container's link | its repository on GitHub, that is `graph_history_url`; if a service runs, also `live_graph_url` |
| An external container's link | a web link to the service itself (`service_url`), for example its website or API documentation |
| Our container's interfaces | derived from its code |
| What our container uses: its integrations, including those with external systems | derived from its code |
| An external container's interfaces | by hand: we have no source code |
| What an external container uses, for example our interface for its webhooks | by hand, for the same reason |
| Links between Software Systems | derived from container links; never entered at all |
| Enterprises, the map, initiatives, stories, plan steps, owners, access | by hand: these are people's decisions |

The line runs along the source code. Where we have code, Maxitor reads the facts from it, and nobody duplicates them. Where there is no code — an external container — only a person can enter the fact.

## What the graph must provide

For our container's interfaces and integrations to be derived from code, the container's graph must know them. Today it does not. Checked on the graphs of the demo and Maxitor, protocol 1.3:

1. **The graph has no adapters.** The FastAPI and MCP adapters expose actions but do not get into the graph. An adapter must print an interface node into the graph, with its name, protocol and exposed actions. One adapter is one interface, as agreed.
2. **A resource has no target.** A `Resource` node carries only a description, so it does not show which container and which interface the resource calls. A resource that calls another container must declare its target in code. Then the graph gets a "resource → target interface" edge.

How to find the graph is already known: through the container's link on GitHub. So the graph itself does not have to name its container.

## Checks

For now the links are not checked: they are derived from code and shown. Reconciling them with tracing — declared and actually called — is the next step.

## What this changes in the mockups

- **New container:** name, kind and one link. For our container it is GitHub and, if there is one, live; for an external one, a web link to the service.
- **Our container's interfaces and links** are read only in Maxitor. Next to them it shows which graph and which version of it they come from.
- **An external container** has "add an interface" and "what it uses" forms.
- **Software System:** it is created by hand, and its containers are chosen from the list of the enterprise's containers.

## Not decided yet

- **How a resource declares its target in code:** by the container's key and the interface's name, or by a link to a specific action of the target.
- **Our container without AOA**, for example a front end, a mobile app or a script: where its interfaces and integrations come from.
- **Our container without its own repository**, for example a database or a queue: what its link is and where its interface comes from. Perhaps the interface is derived from whoever uses it: a resource that declared "claims-db · SQL" as its target defines that interface itself.
