// src/lib/halfPicking.ts
/**
 * One element across the two halves (spec 044): a hover lights it in both, a click selects it in both, and the other
 * half brings it into view or says why it cannot.
 *
 * An element's id on a drawing may be its place there — the third table's second row —, which means nothing to the
 * other half. So what passes between the halves is a ref that names the element by its identity; ``Portable`` turns one
 * into the other. A diagram whose ids are already its identity passes nothing.
 */
import { useEffect, useRef, useState, useSyncExternalStore, type RefObject } from "react";
import { useHalf, type Side } from "@/lib/half";
import { usePageSetting } from "@/lib/pageSettings";
import type { ElementRef } from "@/rooms/focusStore";
import { elementRefOf, elementsOf } from "@/rooms/graphvizFocus";

/** Between a drawing's refs and refs by identity. ``fromIdentity`` gives ``null`` for what this drawing does not hold. */
export type Portable = {
  toIdentity(ref: ElementRef): ElementRef;
  fromIdentity(ref: ElementRef): ElementRef | null;
};

/** What a half answers when an element is selected. */
export type Located = "in_view" | "moved" | "hidden" | "absent";

/** How long "brought to the centre" stands. */
const NOTE_MS = 2500;
/** The farthest a pointer may move during a press that still counts as a click, in CSS px. */
const CLICK_SLOP_PX = 4;
const SELECTED_GLOW = "drop-shadow(0 0 5px rgba(37, 99, 235, 0.95))";
const GLIDE_MS = 320;

let hovers: Record<Side, ElementRef | null> = { a: null, b: null };
const listeners = new Set<() => void>();

/** Say what the pointer is over in half ``side``, by identity. */
export function reportHalfHover(side: Side, ref: ElementRef | null): void {
  if (hovers[side]?.id === ref?.id && hovers[side]?.kind === ref?.kind) return;
  hovers = { ...hovers, [side]: ref };
  for (const listener of listeners) listener();
}

/** What the pointer is over in the half across from ``side``. */
export function hoverAcross(side: Side): ElementRef | null {
  return hovers[side === "a" ? "b" : "a"];
}

/** Hear every change of a half's hover; returns the call that stops. */
export function subscribeHalfHover(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

let areaPicked: string | null = null;

/** Say which area of the full graph holds what was just clicked: the other half reads an area only when asked. */
export function setPickedArea(area: string | null): void {
  areaPicked = area;
}

/** The area of what was clicked last in this tab, or ``null``. */
export function pickedArea(): string | null {
  return areaPicked;
}

/** A pair's steps: each half's way to go to a change, so that one step moves both. */
const steppers = new Map<Side, (index: number) => void>();

/** Hear the pair's steps as half ``side``; returns the call that stops. */
export function joinSteps(side: Side, go: (index: number) => void): () => void {
  steppers.set(side, go);
  return () => {
    if (steppers.get(side) === go) steppers.delete(side);
  };
}

/** Take one step in both halves. */
export function stepBoth(index: number): void {
  for (const go of steppers.values()) go(index);
}

/** Whether ``box`` stands whole inside ``stage``. */
export function inView(box: Pick<DOMRect, "left" | "right" | "top" | "bottom">, stage: Pick<DOMRect, "left" | "right" | "top" | "bottom">): boolean {
  return box.left >= stage.left && box.right <= stage.right && box.top >= stage.top && box.bottom <= stage.bottom;
}

/** What a half says of its answer, or ``null`` when it has nothing to say. */
export function noteOf(located: Located, name: string): string | null {
  if (located === "moved") return "Brought to the centre";
  if (located === "hidden") return "Hidden by the filters";
  if (located === "absent") return `Not in ${name}`;
  return null;
}

type HalfPickingOptions = {
  pannerRef: RefObject<HTMLElement | null>;
  viewportRef: RefObject<HTMLElement | null>;
  centreOnClient(x: number, y: number): void;
  /** Changes whenever the SVG is replaced. */
  drawing: unknown;
  nodeKind: "node" | "table";
  /** Whether this half's version holds the element, shown or not. */
  holds(ref: ElementRef): boolean;
  portable?: Portable | null;
};

/** A drawing whose ids are the elements' identity. */
const SAME: Portable = { toIdentity: (ref) => ref, fromIdentity: (ref) => ref };

/**
 * Select by a click in a Side by side half, and show the selection here: lit, brought into view when it is out of it,
 * and a note when it cannot be. Outside Side by side it does nothing. Returns what the half says.
 */
export function useHalfPicking({ pannerRef, viewportRef, centreOnClient, drawing, nodeKind, holds, portable }: HalfPickingOptions): string | null {
  const half = useHalf();
  const [selected, setSelected] = usePageSetting<ElementRef | null>("selected", null);
  const [note, setNote] = useState<string | null>(null);
  const latest = useRef({ holds, portable: portable ?? SAME, centreOnClient });
  latest.current = { holds, portable: portable ?? SAME, centreOnClient };
  const active = half !== null;

  useEffect(() => {
    const stage = viewportRef.current;
    if (!active || !stage) return undefined;
    const ac = new AbortController();
    let press: { x: number; y: number; target: Element } | null = null;
    stage.addEventListener(
      "pointerdown",
      (event) => {
        press = event.target instanceof Element ? { x: event.clientX, y: event.clientY, target: event.target } : null;
      },
      { capture: true, signal: ac.signal },
    );
    stage.addEventListener(
      "pointerup",
      (event) => {
        const started = press;
        press = null;
        // A press that moved is a pan; a press on the toolbar or a panel is theirs.
        if (!started || Math.hypot(event.clientX - started.x, event.clientY - started.y) > CLICK_SLOP_PX || !pannerRef.current?.contains(started.target) && started.target.closest("button, input, a, [role='group']")) return;
        const ref = elementRefOf(started.target, nodeKind);
        setSelected(ref ? latest.current.portable.toIdentity(ref) : null);
      },
      { capture: true, signal: ac.signal },
    );
    window.addEventListener(
      "keydown",
      (event) => {
        if (event.key === "Escape") setSelected(null);
      },
      { signal: ac.signal },
    );
    return () => ac.abort();
  }, [active, nodeKind, pannerRef, setSelected, viewportRef]);

  useEffect(() => {
    const panner = pannerRef.current;
    const stage = viewportRef.current?.getBoundingClientRect();
    if (!active || !half || !panner || !stage || !selected) {
      setNote(null);
      return undefined;
    }
    const here = latest.current.portable.fromIdentity(selected);
    const elements = here ? elementsOf(panner, here) : [];
    const target = elements.at(-1) as (Element & ElementCSSInlineStyle) | undefined;
    if (!target) {
      setNote(noteOf(latest.current.holds(selected) ? "hidden" : "absent", half.name));
      return undefined;
    }
    target.style.filter = SELECTED_GLOW;
    const box = (elements[0] ?? target).getBoundingClientRect();
    let moved: ReturnType<typeof setTimeout> | undefined;
    if (inView(box, stage)) setNote(null);
    else {
      panner.style.transition = `transform ${GLIDE_MS}ms ease`;
      latest.current.centreOnClient(box.left + box.width / 2, box.top + box.height / 2);
      setNote(noteOf("moved", half.name));
      moved = setTimeout(() => {
        panner.style.transition = "";
        setNote(null);
      }, NOTE_MS);
    }
    return () => {
      target.style.filter = "";
      if (moved !== undefined) clearTimeout(moved);
      panner.style.transition = "";
    };
  }, [active, half, selected, drawing, pannerRef, viewportRef]);

  return note;
}

/** The selection by identity, for what must keep it in sight. */
export function useSelectedElement(): ElementRef | null {
  return usePageSetting<ElementRef | null>("selected", null)[0];
}

/** The hover across from ``side``, followed as it moves. */
export function useHoverAcross(side: Side | null): ElementRef | null {
  return useSyncExternalStore(subscribeHalfHover, () => (side ? hoverAcross(side) : null));
}
