# Quickstart — proving the card's fills follow its contour

**Feature**: `specs/009-erd-card-contour` | **Date**: 2026-10-18

Four ways to see the change work, from cheapest to most convincing. Every command is run from the
repository root unless it says otherwise, and none of them needs a database or a running service.

## 1. The automatic check — the fast proof

```bash
cd packages/aoa-maxitor/client
node scripts/check-erd-card-containment.ts
```

**Before the change**: exit `1`, with A-1 naming the corners that stand outside the contour —

```text
fail  A-1  containment — node1 fill 1 corner (1, -44.6) is outside the inset contour (arc starts at x=12)
```

**After the change**: exit `0`, thirteen `ok` lines and the scale numbers on the last one. This single
command is the FR-013 demonstration: A-1 is the property today's markup violates, and A-8 strips the
inserted clips to prove nothing but the fills' outlines moved.

Each run also prints one line that is **not** an assertion:

```text
info  the renderer still emits rectangles: 4 of 6 cards have a fill corner outside the contour before the pass
```

It is the measurement that the pass is still needed — on the day a renderer rounds its own cells, it
reads zero and the pass becomes removable rather than the check turning red.

## 2. The markup, by eye

```bash
cd packages/aoa-maxitor/client
node scripts/check-erd-card-containment.ts --print-svg > /tmp/card-before-and-after.txt
```

The script's `--print-svg` mode writes the unprocessed and the processed markup for the fixture card,
one after the other behind a marker line, so the difference is readable as text (the file is not one
valid SVG — it is two documents for reading, which is why it is `.txt`). The processed card carries
one `<clipPath id="erd-fill-clip-node1">` whose path is the contour shrunk by 1 with radius 11, and
every fill points at it. Strip those insertions and the two halves are byte-identical — that is what
A-8 asserts and FR-002 … FR-005 read straight off the file.

## 3. The page, on the reproduction link

Open the link from the issue and look at any card:

<https://maxitor.aoa.run/?source=https%3A%2F%2Fadmingameoffer.aoa.run%2Fgraph-json&view=domain-erd>

Walk the five presets in the toolbar, zoom to the maximum, and switch a domain off and on.

**Expected**: every card reads as one shape — the header band's upper corners follow the arcs, a
tinted last row follows the lower arcs, and nothing of a fill stands outside the outline. The
hairline between a fill and the stroke that the renderer's own inset leaves is unchanged from today
(the clarification session accepted it), and no colour is painted under the stroke.

## 4. The guards — what must *not* have changed

```bash
cd packages/aoa-maxitor/client && npm run build
bash scripts/run_checks_with_log.sh
```

Then open the lifecycle automaton and the use-case diagram with the same graph and compare with the
same pages before the change. Both must be identical — their nodes carry a single fill inside their
own outline, and the pass skips them (A-7), while A-10 proves the pass has no other call site and
A-11 proves it pulls in no new package.

## 5. The scale case — 120 cards

The check's last line reports the numbers on a fixture of 120 tables:

```text
ok    A-12 scale — 120 cards rendered and processed in 312 ms (budget 2000 ms)
```

For the frame timing SC-007 asks for, record the same fixture in the page with the browser's own
profiling before and after the change and put both numbers in the pull request. That number is
recorded, not asserted — the check asserts only that the drawing still happens inside a generous
budget.

## Closing two steps

The change is not finished when the picture is right. The repository's last three steps are the
closing check run, the documentation and the changelog — in that order, one article in
`packages/aoa-maxitor/CHANGELOG.md` under `## [Unreleased]` with its `CHANGELOG.ru_draft.md`
counterpart, and the two component READMEs updated (R8).
