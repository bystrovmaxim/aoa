// src/api/elementCard.ts
import { getActiveBase, getActiveSource, graphFetch, type GraphRead } from "@/api/client";

/** What the server says of one node (spec 043, FR-013). */
export type ElementCardRead = { id: string; type: string; label: string; description: string | null; lifecycle_id: string | null };

const kept = new Map<string, Promise<ElementCardRead | null>>();

/** One version's answer: ``null`` when it does not hold the node. */
async function readFrom(id: string, read?: GraphRead): Promise<ElementCardRead | null> {
  const response = await graphFetch("/api/v1/element-card", new URLSearchParams({ id }), read);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`/api/v1/element-card ${response.status}`);
  return (await response.json()) as ElementCardRead;
}

/** A node as the shown version has it, else as the older version of a comparison does: a removed element is only there. */
async function read(id: string): Promise<ElementCardRead | null> {
  const base = getActiveBase();
  return (await readFrom(id)) ?? (base ? readFrom(id, base) : null);
}

/** One node's card, read once for what is on screen; a failed read is not kept. */
export function fetchElementCard(id: string): Promise<ElementCardRead | null> {
  const key = `${getActiveBase()?.source ?? ""}|${getActiveSource() ?? ""}|${id}`;
  const known = kept.get(key);
  if (known) return known;
  const answer = read(id);
  kept.set(key, answer);
  answer.catch(() => kept.delete(key));
  return answer;
}

/** Forget what was read: a source was reloaded. */
export function forgetElementCards(): void {
  kept.clear();
}
