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
 * element's tooltip text in a small label beside it — and so does everyone over their own diagram: the native tooltip
 * is taken off, its text kept as ``data-tooltip``, so the two always look alike (spec 038).
 */
import { dimUnpaired, hoverAcross, reportHalfHover, subscribeHalfHover, type Portable } from "@/lib/halfPicking";
import { useHalf } from "@/lib/half";
import { useEffect, useRef } from "react";
import { cardFor, isFollowing, mirroredFocus, reportHover, sameRef, subscribeFocus, type ElementRef } from "@/rooms/focusStore";

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
  // Graphviz's own ``edge<n>`` is a place on one drawing; a line's title is the same on any.
  if (edge) return { kind: "edge", id: /^edge\d+$/.test(edge.id) ? titleOf(edge) : edge.id || titleOf(edge) };
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

/** The tooltip text over ``element``: its link's, taken off the native tooltip, else its title. */
export function tooltipOf(element: Element): string {
  const link = element.querySelector("a");
  const linked = link?.getAttribute("data-tooltip") ?? link?.getAttribute("xlink:title") ?? link?.getAttribute("title");
  return (linked ?? titleOf(element)).trim();
}

/** The namespace of a ``<title>`` taken off the drawing: the browser shows no tooltip for it, the selector ``title`` still finds it. */
const QUIET_TITLE_NS = "urn:maxitor:quiet-title";

/**
 * Take the native tooltips off the drawing in ``root``: a link's text is kept as ``data-tooltip``, and each SVG
 * ``<title>`` — a table's or a line's id, which the browser shows over its frame — becomes an element of the same name
 * and text in another namespace, so whatever reads a node's title still reads it.
 */
export function takeOffNativeTooltips(root: ParentNode): void {
  for (const title of root.querySelectorAll("title")) {
    if (title.namespaceURI !== "http://www.w3.org/2000/svg") continue;
    const quiet = document.createElementNS(QUIET_TITLE_NS, "title");
    quiet.textContent = title.textContent;
    title.replaceWith(quiet);
  }
  for (const link of root.querySelectorAll("a")) {
    const text = link.getAttribute("xlink:title") ?? link.getAttributeNS("http://www.w3.org/1999/xlink", "title") ?? link.getAttribute("title");
    if (text === null) continue;
    link.setAttribute("data-tooltip", text);
    link.removeAttribute("xlink:title");
    link.removeAttributeNS("http://www.w3.org/1999/xlink", "title");
    link.removeAttribute("title");
  }
}

function sendMouse(elements: Element[], type: "mouseenter" | "mouseleave"): void {
  const ordered = type === "mouseenter" ? elements : [...elements].reverse();
  for (const element of ordered) element.dispatchEvent(new MouseEvent(type, { bubbles: false }));
}

/** A tooltip label: ``follow`` for the followed person's hover, ``own`` for your own — both drawn alike. */
function makeLabel(kind: "follow" | "own" = "follow"): HTMLDivElement {
  const label = document.createElement("div");
  label.setAttribute("aria-hidden", "true");
  if (kind === "follow") label.dataset.followTooltip = "";
  else label.dataset.ownTooltip = "";
  Object.assign(label.style, {
    position: "fixed",
    zIndex: "1400",
    pointerEvents: "none",
    maxWidth: "320px",
    padding: "4px 8px",
    borderRadius: "6px",
    background: "#fff",
    color: "#0f172a",
    border: "1px solid rgba(15, 23, 42, 0.1)",
    boxShadow: "0 4px 16px rgba(15, 23, 42, 0.12)",
    font: "11px/1.4 Helvetica, Arial, sans-serif",
    whiteSpace: "pre-wrap",
    display: "none",
  });
  return label;
}

/**
 * Keep ``label`` under ``element`` — the whole table for a table or any of its rows — and inside the window; above it
 * only when there is no room below. The mouse is on the table, so under the card nothing covers the label.
 */
export function placeLabel(label: HTMLDivElement, element: Element): void {
  const box = element.getBoundingClientRect();
  const width = label.offsetWidth;
  const height = label.offsetHeight;
  const left = Math.min(Math.max(4, box.left), window.innerWidth - width - 4);
  const below = box.bottom + 6;
  const top = below + height > window.innerHeight - 4 ? Math.max(4, box.top - height - 6) : below;
  label.style.left = `${left}px`;
  label.style.top = `${top}px`;
}

/** Where a card stands in place of the label (spec 043): the elements under the hover, or ``null`` when it ended. */
export type HoverCards = {
  /** Whether ``ref`` has a card. */
  has(ref: ElementRef): boolean;
  show(ref: ElementRef | null, elements: readonly Element[]): void;
  /** The followed person's card, as they hold it: at once. */
  open(ref: ElementRef, elements: readonly Element[]): void;
  /** A press, a wheel, or the followed person's card gone: no waiting. */
  close(): void;
};

/**
 * Share the hover of the Graphviz drawing inside ``root`` with followers, and show the followed
 * person's. ``drawing`` changes whenever the SVG is replaced, so a mirrored hover is replayed on the
 * new one. ``nodeKind`` names a node: ``table`` on the ERD, ``node`` elsewhere. ``cards`` takes what
 * has a card; the rest keeps its label.
 */
export function useGraphvizFocus(root: HTMLElement | null, drawing: unknown, page: string | null, nodeKind: "node" | "table", cards?: HoverCards, portable?: Portable | null): void {
  const cardsRef = useRef(cards);
  cardsRef.current = cards;
  // In Side by side a hover passes to the other half by identity, the way a followed person's is replayed (spec 044).
  const side = useHalf()?.side ?? null;
  const portableRef = useRef(portable);
  portableRef.current = portable;
  const byIdentity = (ref: ElementRef | null) => (ref && portableRef.current ? portableRef.current.toIdentity(ref) : ref);
  const here = (ref: ElementRef | null) => (ref && portableRef.current ? portableRef.current.fromIdentity(ref) : ref);
  // A half reports its hover by identity too: a follower's two halves light it as the leader's do.
  const toAcross = (ref: ElementRef | null) => {
    if (side) reportHalfHover(side, byIdentity(ref));
    reportHover(side ? byIdentity(ref) : ref);
  };
  // No native tooltip on any drawing: the app's own label shows instead, the same for everyone. The viewer places its
  // SVG after this hook's effects run, and may place it again, so every new drawing is caught as it lands.
  useEffect(() => {
    if (!root) return undefined;
    takeOffNativeTooltips(root);
    const observer = new MutationObserver(() => takeOffNativeTooltips(root));
    observer.observe(root, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [root]);

  // Your own mouse: report what it is over, and show its tooltip as a follower sees it.
  useEffect(() => {
    if (!root) return undefined;
    const ac = new AbortController();
    const label = makeLabel("own");
    document.body.appendChild(label);
    let shown: ElementRef | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const hide = () => {
      if (timer !== null) clearTimeout(timer);
      timer = null;
      label.style.display = "none";
    };
    const show = (ref: ElementRef | null) => {
      if (sameRef(ref, shown)) return;
      hide();
      shown = ref;
      const elements = ref ? elementsOf(root, ref) : [];
      const carded = ref !== null && cardsRef.current?.has(ref) === true;
      cardsRef.current?.show(carded ? ref : null, elements);
      if (carded) return;
      const anchor = elements.at(-1);
      const text = anchor ? tooltipOf(anchor) : "";
      if (!anchor || !text) return;
      label.textContent = text;
      timer = setTimeout(() => {
        label.style.display = "block";
        placeLabel(label, elements[0]);
      }, TOOLTIP_DELAY_MS);
    };
    const onOver = (event: MouseEvent) => {
      if (!event.isTrusted || isFollowing() || !(event.target instanceof Element)) return;
      const ref = elementRefOf(event.target, nodeKind);
      toAcross(ref);
      // A press is a drag on its way: what passes under the pointer then is not being looked at.
      if (event.buttons === 0) show(ref);
    };
    const onLeave = (event: MouseEvent) => {
      if (!event.isTrusted || isFollowing()) return;
      toAcross(null);
      show(null);
    };
    // A press or a wheel hides it, as a native tooltip goes away.
    const dismiss = () => {
      show(null);
      cardsRef.current?.close();
    };
    root.addEventListener("pointerdown", dismiss, { signal: ac.signal });
    root.addEventListener("wheel", dismiss, { signal: ac.signal, passive: true });
    ac.signal.addEventListener("abort", () => {
      hide();
      label.remove();
    });
    // A follower's own mouse is held back before it reaches the viewer's handlers.
    const holdBack = (event: Event) => {
      if (event.isTrusted && isFollowing()) event.stopPropagation();
    };
    root.addEventListener("mouseover", onOver, { signal: ac.signal });
    root.addEventListener("mouseleave", onLeave, { signal: ac.signal });
    for (const type of HELD_BACK) root.addEventListener(type, holdBack, { capture: true, signal: ac.signal });
    return () => ac.abort();
  }, [root, nodeKind, side]);

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
      const outer = entered[0];
      if (label.style.display === "none" || !outer) return;
      placeLabel(label, outer);
      frame = requestAnimationFrame(follow);
    };
    const hideLabel = () => {
      if (labelTimer !== null) clearTimeout(labelTimer);
      labelTimer = null;
      label.style.display = "none";
    };
    const apply = () => {
      const focus = mirroredFocus();
      const across = side ? hoverAcross(side) : null;
      const hover = focus && focus.page === page ? (side ? here(focus.hover) : focus.hover) : here(across);
      if (side && across && !hover) dimUnpaired(root, "hover", true);
      if (sameRef(hover, shown) && (hover === null || entered.length > 0)) return;
      sendMouse(entered, "mouseleave");
      hideLabel();
      shown = hover;
      entered = hover ? elementsOf(root, hover) : [];
      sendMouse(entered, "mouseenter");
      // What the other half points at has no pair here: this half goes out (spec 044).
      if (side) dimUnpaired(root, "hover", across !== null && entered.length === 0);
      // A hover from the other half lights; its card and label stand under the pointer, there (FR-015).
      if (!focus || (hover !== null && cardsRef.current?.has(hover) === true)) return;
      const anchor = entered.at(-1);
      const text = anchor && focus?.tooltip && sameRef(focus.tooltip, hover) ? tooltipOf(anchor) : "";
      if (!text) return;
      label.textContent = text;
      labelTimer = setTimeout(() => {
        label.style.display = "block";
        follow();
      }, TOOLTIP_DELAY_MS);
    };
    // The followed person's card goes by what they say of it, not by their hover: on the card they hover nothing.
    let card: ElementRef | null = null;
    const applyCard = () => {
      const focus = mirroredFocus();
      if (!focus) return;
      const said = focus.page === page ? cardFor(focus.panels, side) : null;
      if (sameRef(said, card)) return;
      card = said;
      if (said) cardsRef.current?.open(said, elementsOf(root, said));
      else cardsRef.current?.close();
    };
    const applyAll = () => {
      apply();
      applyCard();
    };
    applyAll();
    const unsubscribe = subscribeFocus(applyAll);
    const stopAcross = subscribeHalfHover(apply);
    return () => {
      unsubscribe();
      stopAcross();
      sendMouse(entered, "mouseleave");
      hideLabel();
      if (frame !== null) cancelAnimationFrame(frame);
      label.remove();
    };
  }, [root, drawing, page, side]);
}
