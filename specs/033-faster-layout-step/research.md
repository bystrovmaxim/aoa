# Research: A Faster Three-Engine Layout Step That Checks Exactly as Much

Decisions for [spec.md](spec.md), checked against `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts` on 2026-10-28.

## R1. Timing the parts

- **Decision**: `main` notes the time before and after each part and prints, before today's summary line, one line per part — `part A (layout hashes) 25.2 s`, `part B (pointer in a room) 7.2 s`, `part C (following) 27.5 s` — and today's summary keeps its total. Once parts overlap (R4), each line still gives that part's own duration, from its start to its end.
- **Rationale**: FR-002; the lines are added, none is changed (FR-003).

## R2. The six pairs side by side

- **Decision**: part C starts all six `followCase` calls at once and waits for all of them; it prints their lines afterwards, in today's pair order (for each leading engine in `ENGINES` order, each other engine as follower). Every call keeps opening its own new room through "Open room", so no two pairs share a room.
- **Rationale**: FR-004, FR-003. Six pairs × 4.6 s one after another is 27.5 s; side by side the part should take about as long as its slowest pair.
- **Risk**: twelve browsers at once (two per pair) beside the rest of the check run. The hover limit is 500 ms against measured 18–45 ms, so there is margin; the ten runs of FR-009 confirm it. If it fails, a smaller number at once (for example by leading engine, three groups of two) is the fallback, measured the same way.
- **Alternatives considered**: one browser per engine shared by its pairs. Rejected: the pair would share a browser process between rooms, which today's check does not do.

## R3. The two screen sizes side by side

- **Decision**: `runEngine` creates both contexts — 375×812 and 1600×900 — and lays out the targets in both at once, each in its own fresh context as today. The results map is filled as now; the report no longer relies on the order in which keys were first inserted: it walks the targets in the left panel's order and, within a target, its modes in the order the page lists them, and within a `DIFF` lists the runs in engine-then-size order.
- **Rationale**: FR-005, FR-003. With sizes side by side, which context reaches a page first is a matter of timing; the output must not be.
- **Alternatives considered**: a browser per size. Rejected: twice the browser processes for no change in what is checked.

## R4. Part B beside the rest

- **Decision**: `main` starts part A, part B and part C at once and waits for all three; it then prints part A's report, part B's lines and part C's lines, in that order, and the part times.
- **Rationale**: FR-006, FR-003, FR-007 — every part prints and every `DIFF` counts, whichever part ends first.
- **Risk**: the most browsers at once (part A's three browsers with two contexts each, part B's three, part C's twelve). Phase 4 is measured on its own and reverted if it does not help (FR-008).

## R5. The deliberate breaks

- **Decision**: one at a time, each restored, each in the step's own inputs to its comparisons (FR-010 keeps Maxitor out of the change): Firefox's hash for one page-mode at one size gets a suffix → `DIFF` naming that page-mode; WebKit's pointer offsets get 3 px added → the pointer case fails; one pair's `apartPx` gets 3 px added → that pair fails. Each must also leave the other parts' lines as they were and the exit code 1.

## R6. Measuring

- **Decision**: each phase is measured alone (the step twice on its own) and inside the check run (its step time and the run's wall time), on the M3 Max, and recorded in `tasks.md`; the baseline and the final comparison are posted on #298. Ten check runs in a row close the work (FR-009).

## R7. Documentation

- **Decision**: the how-to page `docs/how-to/run-the-checks.md` (from #279) gets its "What runs together and what waits" and longest-chain numbers updated, and one sentence on the layout step's three parts. No `examples/` script or notebook, as the maintainer decided for #279 (the cases are shell commands on the whole repository).
