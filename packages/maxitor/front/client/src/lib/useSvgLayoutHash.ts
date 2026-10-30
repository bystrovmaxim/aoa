// src/lib/useSvgLayoutHash.ts
/**
 * The layout hash of a Graphviz picture and the settings digest of its input, for the `data-layout-hash` and
 * `data-layout-input` attributes of its viewer.
 *
 * The hash is taken over the SVG Graphviz returned, before any post-pass, so it changes exactly
 * when a node moves (contracts/layout-determinism.md). The pair is `undefined` while there is no
 * picture or while a new one is being hashed, so the attributes never describe a picture that is no
 * longer on screen, nor one picture under another's input.
 */
import { useEffect, useRef, useState } from "react";

import { svgLayoutHash } from "./layoutHash";

/**
 * The layout hash of the Graphviz picture ``svg`` and the settings digest of the text ``input`` it was laid out from,
 * as one pair: both, or neither while either is being computed. Hashed apart, the two came in at different moments, and
 * a tab drawing new filters reported its new picture under no digest at all — the room then took a picture laid out
 * alike for another, and turned pointers off (spec 038). ``input`` is bound to ``svg`` when ``svg`` changes: the
 * viewer's render of an earlier input is cancelled before it can set its picture, so the input on hand then is the
 * one the picture came from.
 */
export function useSvgLayoutPair(svg: string, input: string): { hash: string; digest: string } | undefined {
  const bound = useRef({ svg: "", input: "" });
  if (bound.current.svg !== svg) bound.current = { svg, input };
  const inputOfSvg = bound.current.input;
  const [hashed, setHashed] = useState<{ svg: string; input: string; hash: string; digest: string } | null>(null);

  useEffect(() => {
    if (!svg) return undefined;
    let cancelled = false;
    void Promise.all([svgLayoutHash(svg), svgLayoutHash(inputOfSvg)]).then(([hash, digest]) => {
      if (!cancelled) setHashed({ svg, input: inputOfSvg, hash, digest });
    });
    return () => {
      cancelled = true;
    };
  }, [svg, inputOfSvg]);

  return svg && hashed?.svg === svg && hashed.input === inputOfSvg ? { hash: hashed.hash, digest: hashed.digest } : undefined;
}
