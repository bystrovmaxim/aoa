# Quickstart: accepting Maxitor Rooms Polish phase by phase

## The local stand

Rebuilt by the agent after every phase, from the repository root:

```bash
bash scripts/deploy_demonstrator_stand.sh --local
```

- Maxitor: `http://127.0.0.1:8101`; in the service field enter `http://demo:8100` (the demo, reached inside the stand's network).
- Rooms need two people: a second browser, or a private window of the same one.
- The script ends with `stand verified`; if it rolls back, the phase is not ready.

## Per phase

After each phase the agent (1) runs that phase's tests and checks, (2) rebuilds the stand and checks the phase there itself, (3) gives the maintainer, in Russian, what to open, what to do and what must be seen. The commit follows the maintainer's acceptance and instruction.

| phase | what to check on the stand |
|---|---|
| Room picture on open | set filters and Neato, open a room, join in the second browser: the same diagram; open another page: still the same |
| Pointers stay | keep the mouse still for a minute: the other browser still shows the pointer; leave the room: it disappears |
| Follow mirrors focus | follow, then hover, open a tooltip, select a node, open *Kinds* and a sidebar branch in the followed browser: the follower shows each |
| Smooth follow | pan and zoom quickly in the followed browser: the follower glides, then stands exactly where the leader stopped |
| Firefox follow | follow in each direction between Firefox and Chrome (and Safari) |
| Room controls | circles 22 px with a gap, never touching with any ring; buttons 32 px, icons 16 px; switch whom you follow — nothing overlaps |
| ERD card | header flush with the outline, the mockup's corner curve |
| Icon axis | the kind icon centred on the table name |
| Clean field types | `str \| None`, `CurrencyEnumEntity`, `X[]` …; the full annotation in the tooltip |
| ERD line ends | optional vs mandatory ends differ; dictionary lines have the crow's foot at the referring table |
| ERD hover | hover a PK, an FK and a line: every joined table stays bright |
| Role labels | use-case diagram: labels appear only on hover |
| Kinds filter | a diagram without some kinds lists only its own |
| Maxitor's own graph | enter `http://127.0.0.1:8101` (or the stand's own address) in the service field: Maxitor's diagram opens |

## Automated proof

- `bash scripts/run_checks_with_log.sh` — the closing run, including the cross-engine check with the new follow case and the ERD style check with the card, axis and line-end measurements.
- Freshness by hand: `curl -si http://127.0.0.1:8101/examples/model/graph-json | grep -i etag`, then the same with `-H 'If-None-Match: <tag>'` → `304`.
