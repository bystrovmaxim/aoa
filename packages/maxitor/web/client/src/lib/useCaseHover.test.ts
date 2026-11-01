// src/lib/useCaseHover.test.ts
import { describe, expect, it } from "vitest";
import { bindUseCaseHover, litBy } from "@/lib/useCaseHover";

const LINKS = ["r_a->a_x", "r_a->a_y", "a_x->a_z", "r_b->a_w"];

describe("what a hover keeps lit", () => {
  it("of a node: the node, its links and their other ends, and nothing further", () => {
    const lit = litBy("a_x", LINKS);
    expect([...lit.links]).toEqual(["r_a->a_x", "a_x->a_z"]);
    expect([...lit.nodes].sort()).toEqual(["a_x", "a_z", "r_a"]);
  });

  it("of a role: every action it serves", () => {
    expect([...litBy("r_a", LINKS).nodes].sort()).toEqual(["a_x", "a_y", "r_a"]);
  });

  it("of a link: the link and its two ends", () => {
    const lit = litBy("a_x->a_z", LINKS);
    expect([...lit.links]).toEqual(["a_x->a_z"]);
    expect([...lit.nodes].sort()).toEqual(["a_x", "a_z"]);
  });

  it("of a node with no links: the node alone", () => {
    const lit = litBy("r_lonely", LINKS);
    expect([...lit.nodes]).toEqual(["r_lonely"]);
    expect(lit.links.size).toBe(0);
  });
});

describe("the hover on a drawing", () => {
  it("gives each link a wide area and keeps the nodes above the links", () => {
    const root = document.createElement("div");
    root.innerHTML = '<svg><g class="graph"><g class="node"><title>a_x</title></g><g class="edge"><title>r_a-&gt;a_x</title><path d="M0 0L9 9"/></g></g></svg>';
    bindUseCaseHover(root, new AbortController().signal);
    expect(root.querySelector("g.edge path.erd-hit")).not.toBeNull();
    expect([...root.querySelector("g.graph")!.children].map((child) => child.getAttribute("class"))).toEqual(["edge", "node"]);
  });

  it("dims the rest on enter and puts everything back on leave", () => {
    const root = document.createElement("div");
    root.innerHTML = '<svg><g class="node"><title>a_x</title></g><g class="node"><title>r_a</title></g><g class="node"><title>a_y</title></g><g class="edge"><title>r_a-&gt;a_x</title></g><g class="edge"><title>r_b-&gt;a_y</title></g></svg>';
    bindUseCaseHover(root, new AbortController().signal);
    const nodes = [...root.querySelectorAll<SVGElement>("g.node")];
    const edges = [...root.querySelectorAll<SVGElement>("g.edge")];
    nodes[0].dispatchEvent(new MouseEvent("mouseenter"));
    expect(nodes.map((node) => node.style.opacity)).toEqual(["1", "1", "0.35"]);
    expect(edges.map((edge) => edge.style.opacity)).toEqual(["1", "0.2"]);
    nodes[0].dispatchEvent(new MouseEvent("mouseleave"));
    expect([...nodes, ...edges].map((element) => element.style.opacity)).toEqual(["", "", "", "", ""]);
  });
});
