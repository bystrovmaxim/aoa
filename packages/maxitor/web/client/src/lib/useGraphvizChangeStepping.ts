// src/lib/useGraphvizChangeStepping.ts
/**
 * Stepping through the changes of a diagram Graphviz draws (spec 040, FR-025e; spec 041, FR-016 – FR-019): it offers
 * the changes to the control beside the version button, goes to one, opens its card, mirrors a followed person, and
 * lights what a step arrived at. A diagram gives its changes, each naming the SVG element it stands on.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";
import type { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import { setChangeStepping, type ChangeEntry } from "@/lib/changeStepping";
import { useHalf, writesForPair } from "@/lib/half";
import { joinMirror, joinSteps, mirrorBoth, reportStepCard, stepBoth, useStepCardOpen, type Portable } from "@/lib/halfPicking";
import { usePageSetting } from "@/lib/pageSettings";
import type { ElementRef } from "@/rooms/focusStore";
import { elementRefOf } from "@/rooms/graphvizFocus";
import { MARK_LOOK, type CardTarget } from "@/lib/erdDiffCard";
import { isFollowing } from "@/rooms/focusStore";

/** One change a Graphviz diagram draws: what it steps to, and its card where it has one. */
export type GraphvizChange = ChangeEntry & { cell: string; card: CardTarget | null };

/** An open card and where it stands, in the stage's pixels. */
export type OpenCard = { target: CardTarget; at: { x: number; y: number } };

/** The card's width, so that it stays on the stage beside what a step arrived at. */
const CARD_WIDTH_PX = 312;
/** The room kept under a card's top edge; more of it scrolls inside the card. */
const CARD_ROOM_PX = 320;
/** A step never leaves the picture smaller than this: what it arrives at must be readable. */
const STEP_SCALE = 0.85;

/** Where a card asked for at ``x``, ``y`` stands so that it stays on a stage of ``box``'s size. */
export function cardPlace(box: { width: number; height: number }, x: number, y: number): { x: number; y: number } {
  return { x: Math.max(8, Math.min(x, box.width - CARD_WIDTH_PX)), y: Math.max(8, Math.min(y, box.height - CARD_ROOM_PX)) };
}

export type GraphvizChangeSteppingOptions = {
  changes: readonly GraphvizChange[];
  pannerRef: RefObject<HTMLElement | null>;
  viewportRef: RefObject<HTMLElement | null>;
  panZoom: Pick<ReturnType<typeof useSvgPanZoom>, "getScale" | "setScale" | "centreOnClient" | "onTransform">;
  /** The drawing on screen: a new one needs its light again. */
  svgMarkup: string;
  /** What names a node on this drawing, and the refs across a pair; for Side by side. */
  nodeKind?: "node" | "table";
  portable?: Portable | null;
};

/** The card and the position of a Graphviz diagram's steps, and ``openCard`` for a click that opens one. */
export function useGraphvizChangeStepping({ changes, pannerRef, viewportRef, panZoom, svgMarkup, nodeKind = "node", portable }: GraphvizChangeSteppingOptions) {
  const half = useHalf();
  const writesPair = writesForPair(half);
  const [, setSelected] = usePageSetting<ElementRef | null>("selected", null);
  const [card, setCard] = useState<OpenCard | null>(null);
  const changesRef = useRef(changes);
  changesRef.current = changes;
  const [position, setPosition] = useState<number | null>(null);
  useEffect(() => setPosition(null), [changes]);
  const cellOf = useCallback((index: number) => pannerRef.current?.querySelector<SVGElement>(`[id="${changesRef.current[index]?.cell}"]`) ?? null, [pannerRef]);
  const showCard = useCallback(
    (index: number) => {
      const target = changesRef.current[index]?.card;
      const box = viewportRef.current?.getBoundingClientRect();
      const cell = cellOf(index)?.getBoundingClientRect();
      setCard(target && box && cell ? { target, at: cardPlace(box, cell.right - box.left + 8, cell.top - box.top) } : null);
    },
    [cellOf, viewportRef],
  );
  const goToChange = useCallback(
    (index: number) => {
      setPosition(index);
      setCard(null);
      if (half && !cellOf(index)) return;
      if (panZoom.getScale() < STEP_SCALE) panZoom.setScale(STEP_SCALE);
      const cell = cellOf(index)?.getBoundingClientRect();
      if (cell) panZoom.centreOnClient(cell.left + cell.width / 2, cell.top + cell.height / 2);
      const element = half ? cellOf(index) : null;
      const ref = element ? elementRefOf(element, nodeKind) : null;
      // A step is a click: it selects in both; the card stands in B, or in A for what only A has (spec 044, FR-014).
      if (ref) setSelected(portable ? portable.toIdentity(ref) : ref);
      if (half?.side !== "a" || changesRef.current[index]?.status === "removed") showCard(index);
    },
    [cellOf, half, nodeKind, panZoom, portable, setSelected, showCard],
  );
  const mirrorChange = useCallback(
    (index: number | null, open: boolean) => {
      setPosition(index);
      // A half opens the card where a step does: in B, or in A for what only A has (spec 044).
      const here = half?.side !== "a" || (index !== null && changesRef.current[index]?.status === "removed");
      if (index !== null && open && here) showCard(index);
      else setCard(null);
    },
    [half, showCard],
  );
  /** A card of a change stands by its element, wherever the click was: so it stands for a follower too. */
  const openCard = useCallback(
    (target: CardTarget, at: { x: number; y: number }) => {
      const stepped = changesRef.current.findIndex((change) => change.card?.elements[0]?.id === target.elements[0]?.id);
      setPosition(stepped >= 0 ? stepped : null);
      if (stepped >= 0) showCard(stepped);
      else setCard({ target, at });
    },
    [showCard],
  );
  // A follower's picture glides after the followed person's: the card goes with what it stands by.
  const followed = useRef<number | null>(null);
  followed.current = card ? position : null;
  useEffect(
    () =>
      panZoom.onTransform(() => {
        if (isFollowing() && followed.current !== null) showCard(followed.current);
      }),
    [panZoom.onTransform, showCard],
  );
  const side = half?.side ?? null;
  useEffect(() => (side ? joinSteps(side, goToChange) : undefined), [side, goToChange]);
  useEffect(() => (side ? joinMirror(side, mirrorChange) : undefined), [side, mirrorChange]);
  useEffect(() => {
    if (!side) return undefined;
    reportStepCard(side, card !== null);
    return () => reportStepCard(side, false);
  }, [side, card]);
  const cardOfPair = useStepCardOpen();
  useEffect(() => {
    if (writesPair) setChangeStepping(changes.length ? { entries: changes, position, card: side ? cardOfPair : card !== null, go: side ? stepBoth : goToChange, mirror: side ? mirrorBoth : mirrorChange } : null);
  }, [changes, position, card, cardOfPair, goToChange, mirrorChange, side, writesPair]);
  useEffect(() => () => {
    if (writesPair) setChangeStepping(null);
  }, [writesPair]);
  // The change a step arrived at glows, as it wears a halo on the map.
  useLayoutEffect(() => {
    const change = position === null ? null : changes[position];
    const cell = change ? cellOf(position!) : null;
    if (!change || !cell) return undefined;
    cell.style.filter = `drop-shadow(0 0 5px ${MARK_LOOK[change.status].colour})`;
    return () => {
      cell.style.filter = "";
    };
  }, [position, changes, cellOf, svgMarkup]);
  return { card, setCard, openCard };
}
