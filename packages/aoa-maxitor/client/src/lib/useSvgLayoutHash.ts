// src/lib/useSvgLayoutHash.ts
/**
 * The layout hash of a Graphviz picture, for the `data-layout-hash` attribute of its viewer.
 *
 * The hash is taken over the SVG Graphviz returned, before any post-pass, so it changes exactly
 * when a node moves (contracts/layout-determinism.md). It is `undefined` while there is no
 * picture or while the hash of a new one is being computed, so the attribute never describes a
 * picture that is no longer on screen.
 */
import { useEffect, useState } from "react";

import { svgLayoutHash } from "./layoutHash";

/**
 * Return the layout hash of ``svg``, or ``undefined`` when there is none yet. The same hash of the
 * text Graphviz was given (engine and DOT) is the picture's settings digest: two pictures of the same
 * input must be laid out alike (spec 028, FR-093).
 */
export function useSvgLayoutHash(svg: string): string | undefined {
  const [hashed, setHashed] = useState<{ svg: string; hash: string } | null>(null);

  useEffect(() => {
    if (!svg) return undefined;
    let cancelled = false;
    void svgLayoutHash(svg).then((hash) => {
      if (!cancelled) setHashed({ svg, hash });
    });
    return () => {
      cancelled = true;
    };
  }, [svg]);

  return svg && hashed?.svg === svg ? hashed.hash : undefined;
}
