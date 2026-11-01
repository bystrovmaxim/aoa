// src/lib/half.ts
/**
 * One half of Side by side (spec 044): which version a viewer under it draws, and what of a page is that half's own.
 *
 * A viewer asks ``useHalf``; outside Side by side there is no half, and everything behaves as it always did. Only the
 * layout mode of a page is a half's own among its settings; pan, zoom and the surface are its own by being its viewer's.
 */
import { createContext, createElement, useContext, type ReactNode } from "react";
import type { GraphRead } from "@/api/client";
import type { DiffStatus } from "@/api/compare";

/** A is the older version, on the left; B the newer, on the right. */
export type Side = "a" | "b";

export type Half = {
  side: Side;
  /** The version this half draws, as its own graph reads go. */
  read: GraphRead;
  /** The version's name, for what the half says. */
  name: string;
};

const HalfContext = createContext<Half | null>(null);

export function HalfProvider({ half, children }: { half: Half; children: ReactNode }) {
  return createElement(HalfContext.Provider, { value: half }, children);
}

/** The half this viewer stands in, or ``null`` outside Side by side. */
export function useHalf(): Half | null {
  return useContext(HalfContext);
}

/** The page settings that are the layout mode: each half keeps its own. */
const LAYOUT_SETTINGS: ReadonlySet<string> = new Set(["layout", "rankdir"]);

/** The name setting ``name`` is kept under in ``half``: its own for a layout mode, the shared one for the rest. */
export function settingOfHalf(name: string, half: Half | null): string {
  return half && LAYOUT_SETTINGS.has(name) ? `${name}_${half.side}` : name;
}

/** Whether this viewer writes what a pair has once: counts and steps are B's to write. */
export function writesForPair(half: Half | null): boolean {
  return half?.side !== "a";
}

/** Whether ``side`` draws an element of this status: A has no added element, B no removed one. */
export function drawnOn(side: Side, status: DiffStatus): boolean {
  return status !== (side === "a" ? "added" : "removed");
}
