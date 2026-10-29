// src/components/diagrams/FullGraphViewer/precomputedLayout.ts
/**
 * A G6 layout that returns the positions the worker computed, so G6 draws them the way it draws
 * its own: through the pre-layout it runs before the first element exists.
 *
 * G6 adapts any registered layout through its `layoutAdapter`, which wraps an `@antv/layout`
 * style class and reads its nodes after `execute`. This class follows that shape but imports
 * nothing: the viewer registers it with the G6 module it already loads, and the layout code
 * never enters the chunk every view downloads.
 */

export type PrecomputedNode = { id: string; x: number; y: number };

/** The layout G6 runs when the positions are already known. */
export class PrecomputedLayout {
  readonly id = "precomputed";
  private nodes: PrecomputedNode[] = [];

  /** Take the positions from the layout options; G6 merges them in before this call. */
  execute(_model: unknown, options?: { positions?: Record<string, [number, number]> }): void {
    this.nodes = Object.entries(options?.positions ?? {}).map(([id, [x, y]]) => ({ id, x, y }));
  }

  /** Hand every positioned node to G6, which turns it into the element style. */
  forEachNode(callback: (node: PrecomputedNode) => void): void {
    for (const node of this.nodes) callback(node);
  }

  /** No edge carries a position of its own: G6 draws edges between the nodes. */
  forEachEdge(_callback: (edge: never) => void): void {
    /* nothing to report */
  }
}
