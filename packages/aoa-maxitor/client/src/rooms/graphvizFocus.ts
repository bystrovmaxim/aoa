// src/rooms/graphvizFocus.ts
/**
 * Hover and tooltip of a Graphviz diagram (ERD, use case, lifecycle) shared with followers
 * (spec 029, FR-010 … FR-012).
 *
 * The person followed: every real ``mouseover`` names the element under the mouse — a table row, a
 * line, or a node — and reports it. The follower: their own mouse on the diagram is held back while
 * they follow, and the followed person's hover is replayed by sending ``mouseenter`` / ``mouseleave``
 * to the same elements, so the viewer's own hover code dims, raises and marks exactly as it does for
 * a real mouse. A browser cannot be made to show a native tooltip, so the follower sees the hovered
 * element's tooltip text in a small label beside it.
 */
import { useEffect } from "react";
import { isFollowing, mirroredFocus, reportHover, sameRef, subscribeFocus, type ElementRef } from "@/rooms/focusStore";

/** Mouse events a follower's own mouse may not deliver to the diagram while following. */
const HELD_BACK = ["mouseover", "mouseout", "mouseenter", "mouseleave", "click", "dblclick"] as const;
/** How long the follower's label waits, as a browser waits before showing a tooltip. */
const TOOLTIP_DELAY_MS = 500;

const ROW_CELL = 'g[id^="a_fn"], g[id^="a_ft"]';

function titleOf(element: Element): string {
  return element.querySelector(":scope > title")?.textContent?.trim() ?? "";
}

/** The element under ``target`` a hover names: a table row, else a line, else a node; ``null`` outside them. */
export function elementRefOf(target: Element, nodeKind: "node" | "table"): ElementRef | null {
  const cell = target.closest(ROW_CELL);
  if (cell) return { kind: "row", id: cell.id.slice(2) };
  const edge = target.closest("g.edge");
  if (edge) return { kind: "edge", id: edge.id || titleOf(edge) };
  const node = target.closest("g.node");
  const title = node ? titleOf(node) : "";
  return title ? { kind: nodeKind, id: title } : null;
}

/** The elements a hover of ``ref`` enters, outermost first; the last one carries its tooltip. */
export function elementsOf(root: ParentNode, ref: ElementRef): Element[] {
  if (ref.kind === "row") {
    const cell = [...root.querySelectorAll(ROW_CELL)].find((e) => e.id === `a_${ref.id}`);
    const node = cell?.closest("g.node");
    return [node, cell].filter((e): e is Element => e != null);
  }
  const selector = ref.kind === "edge" ? "g.edge" : "g.node";
  const found = [...root.querySelectorAll(selector)].find((e) => (ref.kind === "edge" && e.id === ref.id) || titleOf(e) === ref.id);
  return found ? [found] : [];
}

/** The tooltip text a browser would show over ``element``. */
export function tooltipOf(element: Element): string {
  const link = element.querySelector("a");
  const linked = link?.getAttribute("xlink:title") ?? link?.getAttribute("title");
  return (linked ?? titleOf(element)).trim();
}

function sendMouse(elements: Element[], type: "mouseenter" | "mouseleave"): void {
  const ordered = type === "mouseenter" ? elements : [...elements].reverse();
  for (const element of ordered) element.dispatchEvent(new MouseEvent(type, { bubbles: false }));
}

function makeLabel(): HTMLDivElement {
  const label = document.createElement("div");
  label.setAttribute("aria-hidden", "true");
  label.dataset.followTooltip = "";
  Object.assign(label.style, {
    position: "fixed",
    zIndex: "1400",
    pointerEvents: "none",
    maxWidth: "320px",
    padding: "4px 8px",
    borderRadius: "4px",
    background: "rgba(97, 97, 97, 0.92)",
    color: "#fff",
    font: "11px/1.4 Helvetica, Arial, sans-serif",
    whiteSpace: "pre-wrap",
    display: "none",
  });
  return label;
}

/** Keep ``label`` beside ``element`` and inside the window. */
function placeLabel(label: HTMLDivElement, element: Element): void {
  const box = element.getBoundingClientRect();
  const width = label.offsetWidth;
  const height = label.offsetHeight;
  const left = Math.min(Math.max(4, box.left), window.innerWidth - width - 4);
  const below = box.bottom + 6;
  const top = below + height > window.innerHeight - 4 ? Math.max(4, box.top - height - 6) : below;
  label.style.left = `${left}px`;
  label.style.top = `${top}px`;
}

/**
 * Share the hover of the Graphviz drawing inside ``root`` with followers, and show the followed
 * person's. ``drawing`` changes whenever the SVG is replaced, so a mirrored hover is replayed on the
 * new one. ``nodeKind`` names a node: ``table`` on the ERD, ``node`` elsewhere.
 */
export function useGraphvizFocus(root: HTMLElement | null, drawing: unknown, page: string | null, nodeKind: "node" | "table"): void {
  // The followed person's own mouse: report what it is over.
  useEffect(() => {
    if (!root) return undefined;
    const ac = new AbortController();
    const onOver = (event: MouseEvent) => {
      if (!event.isTrusted || isFollowing() || !(event.target instanceof Element)) return;
      reportHover(elementRefOf(event.target, nodeKind));
    };
    const onLeave = (event: MouseEvent) => {
      if (event.isTrusted && !isFollowing()) reportHover(null);
    };
    // A follower's own mouse is held back before it reaches the viewer's handlers.
    const holdBack = (event: Event) => {
      if (event.isTrusted && isFollowing()) event.stopPropagation();
    };
    root.addEventListener("mouseover", onOver, { signal: ac.signal });
    root.addEventListener("mouseleave", onLeave, { signal: ac.signal });
    for (const type of HELD_BACK) root.addEventListener(type, holdBack, { capture: true, signal: ac.signal });
    return () => ac.abort();
  }, [root, nodeKind]);

  // The follower: replay the followed person's hover on this drawing and show its tooltip.
  useEffect(() => {
    if (!root) return undefined;
    let entered: Element[] = [];
    let shown: ElementRef | null = null;
    let labelTimer: ReturnType<typeof setTimeout> | null = null;
    let frame: number | null = null;
    const label = makeLabel();
    document.body.appendChild(label);

    const follow = () => {
      if (frame !== null) cancelAnimationFrame(frame);
      frame = null;
      const anchor = entered.at(-1);
      if (label.style.display === "none" || !anchor) return;
      placeLabel(label, anchor);
      frame = requestAnimationFrame(follow);
    };
    const hideLabel = () => {
      if (labelTimer !== null) clearTimeout(labelTimer);
      labelTimer = null;
      label.style.display = "none";
    };
    const apply = () => {
      const focus = mirroredFocus();
      const hover = focus && focus.page === page ? focus.hover : null;
      if (sameRef(hover, shown) && (hover === null || entered.length > 0)) return;
      sendMouse(entered, "mouseleave");
      hideLabel();
      shown = hover;
      entered = hover ? elementsOf(root, hover) : [];
      sendMouse(entered, "mouseenter");
      const anchor = entered.at(-1);
      const text = anchor && focus?.tooltip && sameRef(focus.tooltip, hover) ? tooltipOf(anchor) : "";
      if (!text) return;
      label.textContent = text;
      labelTimer = setTimeout(() => {
        label.style.display = "block";
        follow();
      }, TOOLTIP_DELAY_MS);
    };
    apply();
    const unsubscribe = subscribeFocus(apply);
    return () => {
      unsubscribe();
      sendMouse(entered, "mouseleave");
      hideLabel();
      if (frame !== null) cancelAnimationFrame(frame);
      label.remove();
    };
  }, [root, drawing, page]);
}
