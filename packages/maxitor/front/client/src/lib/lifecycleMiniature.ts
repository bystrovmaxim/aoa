// src/lib/lifecycleMiniature.ts
/**
 * A lifecycle drawn small for a card (spec 043, FR-016, FR-019): read and drawn only when its card opens, and kept for the
 * version or pair on screen, so opening it again costs nothing. A comparison marks it as the full diagram does.
 */
import { getActiveBase, getActiveSource } from "@/api/client";
import { loadGraphvizWasm } from "@/components/diagrams/ErdViewer/hooks/useGraphviz";
import { buildLifecycleFsmDotSource } from "@/lib/buildLifecycleFsmDotSource";
import { nothingChanged } from "@/lib/erdDiff";
import { lifecycleCounts, loadLifecycle, loadLifecycleDiff, unmarkedLifecycle } from "@/lib/lifecycleDiff";

const kept = new Map<string, Promise<string | null>>();

/** Graphviz's drawing, ready to scale to a card: its size comes from the ``viewBox``, and no native tooltip is left in it. */
export function fittedSvg(svg: string): string {
  return svg
    .replace(/<\?xml[\s\S]*?\?>|<!DOCTYPE[\s\S]*?>/g, "")
    .replace(/<svg width="[^"]*" height="[^"]*"/, "<svg")
    .replace(/<title>[^<]*<\/title>/g, "")
    .replace(/ xlink:title="[^"]*"/g, "");
}

async function drawMiniature(lifecycleId: string): Promise<string | null> {
  const diffing = getActiveBase() !== null;
  const read = await (diffing ? loadLifecycleDiff(lifecycleId) : loadLifecycle(lifecycleId));
  if (!read) return null;
  const data = diffing && nothingChanged(lifecycleCounts(read)) ? unmarkedLifecycle(read) : read;
  const graphviz = await loadGraphvizWasm();
  return fittedSvg(graphviz.layout(buildLifecycleFsmDotSource(data, "LR"), "svg", "dot"));
}

/** The drawing of ``lifecycleId`` in what is on screen; ``null`` when no version holds it. A failed read is not kept. */
export function lifecycleMiniature(lifecycleId: string): Promise<string | null> {
  const key = `${getActiveBase()?.source ?? ""}|${getActiveSource() ?? ""}|${lifecycleId}`;
  const known = kept.get(key);
  if (known) return known;
  const drawn = drawMiniature(lifecycleId);
  kept.set(key, drawn);
  drawn.catch(() => kept.delete(key));
  return drawn;
}

/** Forget what was drawn: a source was reloaded. */
export function forgetMiniatures(): void {
  kept.clear();
}
