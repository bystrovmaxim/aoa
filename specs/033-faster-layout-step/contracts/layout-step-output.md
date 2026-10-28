# Contract: The Layout Step's Output

What the check run's log shows for "Maxitor client: the same layout in three engines", and what may not change.

## Lines, in order

1. One line per page-mode, in the left panel's order, modes in the order the page lists them:
   - `ok    <page> | <mode>  <hash, 16 characters>`, or
   - `DIFF  <page> | <mode>` followed by one indented line per engine and size (`<engine> <size>: <hash>`), in engine order (chromium, firefox, webkit) then size order (375x812, 1600x900), and `<n> run(s) gave no hash` when one is missing.
2. One line per engine, in engine order: `ok    pointer in a room | <engine>  largest offset … px (…)` or `DIFF …`.
3. One line per directed pair, leading engine in engine order, then each other engine: `ok    following | <lead> → <follow>  screens apart … px, hover after … ms, circles … px apart, card buttons overrun … px` or `DIFF …`.
4. **New:** `part A (layout hashes) <s> s`, `part B (pointer in a room) <s> s`, `part C (following) <s> s`.
5. `<n> page-modes × 3 engines × 2 sizes in <s> s`.

## Exit code

0 when every line of 1–3 is `ok`; 1 otherwise, after all parts have ended and printed. A failure before the parts (the API does not start) exits 1 with the error, as today.

## What may differ between runs

Times, and the hover milliseconds and pixel figures that vary by themselves. Nothing else.
