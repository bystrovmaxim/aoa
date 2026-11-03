// src/lib/useCaseHover.ts
/**
 * Hover on a use-case diagram, as on the ERD: the element under the mouse, its links and what they reach stay lit, the
 * rest dims. Graphviz titles a node by its name and a link ``<source>-><target>``, which is all this needs. A follower
 * gets the same through the ``mouseenter`` the room replays.
 */
import { addEdgeHitAreas, clearTableFocus, focusTables } from "@/lib/erdPostPass";

/** The title Graphviz gave a node or a link. */
function titleOf(element: Element): string {
  return element.querySelector(":scope > title")?.textContent?.trim() ?? "";
}

/** A link's two ends, from its title. */
function endsOf(link: string): [string, string] {
  const [source = "", target = ""] = link.split("->");
  return [source, target];
}

/** What a hover keeps lit: of a node, the node, its links and their other ends; of a link, the link and its ends. */
export function litBy(hovered: string, links: readonly string[]): { nodes: Set<string>; links: Set<string> } {
  if (hovered.includes("->")) return { nodes: new Set(endsOf(hovered)), links: new Set([hovered]) };
  const touching = links.filter((link) => endsOf(link).includes(hovered));
  return { nodes: new Set([hovered, ...touching.flatMap(endsOf)]), links: new Set(touching) };
}

/** Light what the mouse is over on the drawing under ``root``, until ``signal`` ends. */
export function bindUseCaseHover(root: HTMLElement, signal: AbortSignal): void {
  // A wide invisible stroke along each link, as on the ERD: a thin line is hard to hit.
  const svg = root.querySelector("svg");
  if (svg) addEdgeHitAreas(svg);
  // Nodes above the links, so that a link's wide area never takes the mouse from a node it passes.
  root.querySelectorAll("g.node").forEach((node) => node.parentNode?.appendChild(node));
  const edges = [...root.querySelectorAll("g.edge")];
  const titles = edges.map(titleOf);
  const onEnter = (event: Event) => {
    const lit = litBy(titleOf(event.currentTarget as Element), titles);
    focusTables(root, lit.nodes, new Set(edges.filter((edge) => lit.links.has(titleOf(edge)))));
  };
  const onLeave = () => clearTableFocus(root);
  root.querySelectorAll("g.node, g.edge").forEach((element) => {
    element.addEventListener("mouseenter", onEnter, { signal });
    element.addEventListener("mouseleave", onLeave, { signal });
  });
}
