# Quickstart: Accepting Side by Side

Stand: local history `erd-full` (`.demo-history`), Vite on `:5173`, history on `:8102`, pair `a=39f03ff4be5a`, `b=459e3be2de3d`. The read key stays in the `#key=` part of the maintainer's link and is never written down.

Open the stand, then add `mode=split` in place of `mode=diff`.

1. **Halves**: on each of the four diagrams A stands left, B right, each marked; pan, zoom and layout mode of one leave the other still. A filter acts on both.
2. **Own layout**: a half's tables stand as in One of that version.
3. **Hover**: either half lights the same element in both.
4. **Locator**: click a table far from the other half's centre: it glides there, zoom unchanged, a note shows, the name is copied. A table only in B: A says "Not in" its version.
5. **Stepper**: a step selects in both; one set of counts.
6. **Reload**: the same view and layout modes return.
7. **Phone**: at phone width, A / B flips, the selection stays centred.
8. **Room, two browsers**: A, B, view, layout mode, filter, selection pass; zoom does not; pan does only while following, half by half; the check takes in both versions.
9. **One and Diff**: unchanged.

Automated: `bash scripts/run_checks_with_log.sh`, with `splitMechanics.ts` in it.
