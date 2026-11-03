// src/lib/eventsExplorer.test.ts
import { describe, expect, it } from "vitest";
import type { EventsExplorerPayload } from "@/model/eventsExplorer";
import { EventsGraph, ROOT_KIND, appliedFilters, explore, links, methodsOff, offeredSections, paintOf, portKey, roots, type Filters, type Mode } from "./eventsExplorer";

const KINDS = ["RegularAspect", "SummaryAspect", "Compensator", "ErrorHandler", "AccessDecide"];

/** The test graph of spec 055, as the server answers it for ``tests/fixtures/explorer_graph.py``. */
function payload(): EventsExplorerPayload {
  const domain = (id: string, vocabulary: boolean) => ({ id, label: id.slice(2), short_label: id.slice(2).toLowerCase(), accent_color: "#6366f1", vocabulary });
  const action = (id: string, domain_id: string) => ({ id, label: id.slice(2), short_label: id.slice(2), domain_id });
  return {
    domains: [domain("d.Identity", true), domain("d.Orders", true), domain("d.Quiet", false), domain("d.Stock", true), domain("d.Support", false)],
    actions: [action("a.Checkout", "d.Orders"), action("a.Ping", "d.Quiet"), action("a.Ticket", "d.Support")],
    events: ["e.Cancelled", "e.Placed", "e.Ticket"].map((id) => ({ id, label: id.slice(2), fields: [] })),
    holds: [
      { domain_id: "d.Orders", event_id: "e.Cancelled" },
      { domain_id: "d.Orders", event_id: "e.Placed" },
      { domain_id: "d.Stock", event_id: "e.Placed" },
    ],
    emits: [
      ...KINDS.map((kind) => ({ action_id: "a.Checkout", method_id: `a.Checkout:${kind}`, method: kind, kind, event_id: "e.Placed" })),
      { action_id: "a.Ticket", method_id: "a.Ticket:open", method: "open", kind: "SummaryAspect", event_id: "e.Placed" },
      { action_id: "a.Ticket", method_id: "a.Ticket:open", method: "open", kind: "SummaryAspect", event_id: "e.Ticket" },
    ],
  };
}

const graph = new EventsGraph(payload());
const all: Filters = { domains: new Set(graph.domains.keys()), off: new Set() };
const screen = (mode: Mode, opened: string[] = [], filters: Filters = all) => explore(roots(mode, filters, graph), new Set(opened), filters, ROOT_KIND[mode], graph);
const portsOf = (shown: ReturnType<typeof screen>, node: string) => (shown.ports.get(node) ?? []).map((port) => `${port.kind}:${port.total}${port.join ? "j" : ""}`);

describe("what a domain says of its events", () => {
  it("counts a vocabulary, an empty one, emitting without one, and none", () => {
    expect(graph.domainCounts("d.Orders")).toEqual({ vocabulary: 2, emittedOnly: 0 });
    expect(graph.domainCounts("d.Identity")).toEqual({ vocabulary: 0, emittedOnly: 0 });
    expect(graph.domainCounts("d.Support")).toEqual({ vocabulary: null, emittedOnly: 2 });
    expect(graph.domainCounts("d.Quiet")).toEqual({ vocabulary: null, emittedOnly: 0 });
  });

  it("counts an empty vocabulary as a domain with events", () => {
    expect(graph.withEvents("d.Identity")).toBe(true);
    expect(graph.withEvents("d.Quiet")).toBe(false);
  });

  it("gives each event its standing", () => {
    expect(["e.Placed", "e.Ticket", "e.Cancelled"].map((id) => graph.eventStatus(id))).toEqual(["emitted_held", "emitted_free", "not_emitted"]);
  });
});

describe("the first layer", () => {
  it("is every domain in Domains mode, those with events first, each group by name, and nothing else", () => {
    const shown = screen("domains");
    expect([...shown.depth.keys()]).toEqual(["domain:d.Identity", "domain:d.Orders", "domain:d.Stock", "domain:d.Support", "domain:d.Quiet"]);
    expect(links(shown, new Set(), graph)).toEqual([]);
  });

  it("is every event in Events mode and every emitting action in Actions mode", () => {
    expect(roots("events", all, graph)).toEqual(["event:e.Cancelled", "event:e.Placed", "event:e.Ticket"]);
    expect(roots("actions", all, graph)).toEqual(["action:a.Checkout", "action:a.Ticket"]);
  });
});

describe("ports by layer", () => {
  it("gives the first layer both its ports, empty ones with zero", () => {
    const shown = screen("domains");
    expect(portsOf(shown, "domain:d.Orders")).toEqual(["events:2", "actions:1"]);
    expect(portsOf(shown, "domain:d.Quiet")).toEqual(["events:0", "actions:1"]);
  });

  it("gives the second layer one port, toward the kind not yet on the path", () => {
    const shown = screen("domains", [portKey("domain:d.Orders", "events")]);
    expect(portsOf(shown, "event:e.Placed")).toEqual(["actions:2"]);
    expect(shown.depth.get("event:e.Placed")).toBe(1);
  });

  it("gives the third layer one joining port toward the first layer's kind, counting what it would join", () => {
    const shown = screen("domains", [portKey("domain:d.Orders", "events"), portKey("event:e.Placed", "actions")]);
    expect(portsOf(shown, "action:a.Ticket")).toEqual(["domain:1j"]);
    expect(portsOf(shown, "action:a.Checkout")).toEqual(["domain:1j"]);
  });

  it("never leads on from the third layer, whatever is opened there", () => {
    const opened = [portKey("domain:d.Orders", "events"), portKey("event:e.Placed", "actions"), portKey("action:a.Ticket", "events")];
    const shown = screen("domains", opened);
    expect(shown.depth.has("event:e.Ticket")).toBe(false);
    expect(Math.max(...shown.depth.values())).toBe(2);
  });

  it("reaches every action of a domain through its actions port, those without events too", () => {
    const shown = screen("events", [portKey("event:e.Placed", "domains"), portKey("domain:d.Orders", "actions")]);
    expect(shown.depth.get("action:a.Checkout")).toBe(2);
    const quiet = screen("domains", [portKey("domain:d.Quiet", "actions")]);
    expect(quiet.depth.get("action:a.Ping")).toBe(1);
    expect(portsOf(quiet, "action:a.Ping")).toEqual(["events:0"]);
  });

  it("hides what a closed port opened, except what another open port still shows", () => {
    const both = screen("domains", [portKey("domain:d.Orders", "events"), portKey("domain:d.Stock", "events")]);
    const one = screen("domains", [portKey("domain:d.Stock", "events")]);
    expect(both.depth.has("event:e.Cancelled")).toBe(true);
    expect(one.depth.has("event:e.Cancelled")).toBe(false);
    expect(one.depth.has("event:e.Placed")).toBe(true);
  });

  it("keeps a port of a node off the screen and applies it when the node comes back", () => {
    const opened = [portKey("event:e.Placed", "actions")];
    expect(screen("domains", opened).depth.has("action:a.Checkout")).toBe(false);
    expect(screen("domains", [...opened, portKey("domain:d.Orders", "events")]).depth.get("action:a.Checkout")).toBe(2);
  });

  it("counts on each port exactly what lies behind it under the filters", () => {
    const filters: Filters = { domains: new Set(["d.Orders", "d.Support"]), off: new Set() };
    const shown = screen("events", [], filters);
    expect(portsOf(shown, "event:e.Placed")).toEqual(["actions:2", "domains:2"]);
  });
});

describe("lines", () => {
  it("join an event to every domain holding it on the neighbouring layer", () => {
    const opened = [portKey("domain:d.Orders", "events")];
    const shown = screen("domains", opened);
    const drawn = links(shown, new Set(opened), graph).map((link) => link.id);
    expect(drawn).toContain("h|d.Orders|e.Placed");
    expect(drawn).toContain("h|d.Stock|e.Placed");
    expect(drawn).toContain("d|d.Support|e.Placed");
  });

  it("do not join layers that are not neighbours until a joining port asks", () => {
    const opened = [portKey("domain:d.Orders", "events"), portKey("event:e.Placed", "actions")];
    const shown = screen("domains", opened);
    expect(links(shown, new Set(opened), graph).some((link) => link.kind === "belongs")).toBe(false);
    const joined = [...opened, portKey("action:a.Ticket", "domain")];
    expect(links(screen("domains", joined), new Set(joined), graph).map((link) => link.id)).toContain("b|a.Ticket");
  });

  it("find the actions that emit an event of a domain in two clicks", () => {
    const opened = [portKey("domain:d.Orders", "events"), portKey("event:e.Placed", "actions")];
    const shown = screen("domains", opened);
    expect([...shown.depth.keys()].filter((node) => node.startsWith("action:"))).toEqual(["action:a.Checkout", "action:a.Ticket"]);
  });
});

describe("filter sections and paint", () => {
  const offered = (mode: Mode, opened: string[] = []) => offeredSections(mode, screen(mode, opened), graph).ids;

  it("offer Domains and Coverage at first in Domains mode, and grow with the screen", () => {
    expect(offered("domains")).toEqual(["domains", "coverage"]);
    expect(offered("domains", [portKey("domain:d.Orders", "events")])).toEqual(["domains", "coverage", "events"]);
    expect(offered("domains", [portKey("domain:d.Orders", "events"), portKey("event:e.Placed", "actions")])).toEqual(["domains", "coverage", "events", "methods"]);
    expect(offered("domains", [portKey("domain:d.Quiet", "actions")])).toEqual(["domains", "coverage", "actions"]);
  });

  it("offer no Coverage outside Domains mode, where its rows do not apply", () => {
    expect(offered("events")).toEqual(["domains", "events"]);
    expect(offered("actions")).toEqual(["domains", "methods"]);
    const off: Filters = { domains: all.domains, off: new Set(["coverage:with"]) };
    expect(roots("events", appliedFilters("events", off), graph)).toHaveLength(3);
    expect(roots("domains", appliedFilters("domains", off), graph)).toEqual(["domain:d.Quiet"]);
  });

  it("keep a section whose rows hide everything it sorts, read from the screen with every row on", () => {
    const off: Filters = { domains: all.domains, off: new Set(["events:emitted_held", "events:emitted_free", "events:not_emitted"]) };
    expect(roots("events", off, graph)).toEqual([]);
    expect(offeredSections("events", screen("events"), graph).ids).toContain("events");
  });

  it("drop what a kind of method switched off emits, an event only it emits included", () => {
    const off: Filters = { domains: all.domains, off: new Set(["methods:SummaryAspect"]) };
    const g = graph.only(methodsOff(off));
    expect(g.emitsOf.has("action:a.Ticket".slice(7))).toBe(false);
    expect(g.eventStatus("e.Ticket")).toBe("not_emitted");
    expect(roots("actions", off, graph, g)).toEqual(["action:a.Checkout"]);
  });

  it("paint by the section chosen while it is on the panel, else by the domains", () => {
    expect(paintOf("methods", ["domains", "methods"])).toBe("methods");
    expect(paintOf("methods", ["domains", "coverage"])).toBe("domains");
  });
});
