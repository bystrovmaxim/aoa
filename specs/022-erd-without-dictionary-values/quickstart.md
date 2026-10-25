# Quickstart — proving the card draws no values

**Feature**: [spec.md](./spec.md) | **Contract**: [contracts/erd-card.md](./contracts/erd-card.md) | **Date**: 2026-10-25

Every command below runs from the repository root unless it says otherwise. The expected output is what the finished change prints, not a paraphrase.

## Prerequisites

- Node 22 or newer (the check scripts are TypeScript run directly by Node).
- `packages/aoa-maxitor/client/node_modules` installed (`npm ci` in that directory).
- The workspace virtual environment for the Python checks (`.venv/bin/python`).

## 1. The client builds

```bash
cd packages/aoa-maxitor/client && npm run build
```

Expected: `✓ built in …`, with the two bundles under `dist/assets/`. The "chunks larger than 500 kB" advisory is accepted and stays (constitution, final section).

## 2. The card draws no values, and does not depend on them

```bash
cd packages/aoa-maxitor/client && node scripts/check-erd-dictionary-values.ts
```

Expected: every assertion passes with no output on failure. What it now asserts, in the order it prints:

| Assertion | What it proves |
| --- | --- |
| no `>Euro<`, no `symbol: €`, no `&lt;safe&gt;` in the DOT | no value text reaches the card |
| no `TOOLTIP="code: …"` in the DOT, no `xlink:title="code: …"` in the SVG | the #249 tooltip retired with its row |
| `buildDotSource(with values)` equals `buildDotSource(values: [])` for 0, 1, 3, 26 and 93 values | the card is independent of the declared count (SC-006) |
| the non-dictionary entity's DOT equals the golden recorded before the change | an ordinary card is unchanged (SC-005) |
| `>amount<` still present, `→ RichEnumEntity` printed once, the arrow present | a non-dictionary card and the reference are untouched |
| the legacy graph renders and invents no edge | an older export still draws |

Until this feature is implemented the script fails — that is the point of it.

## 3. The controls still pass

```bash
cd packages/aoa-maxitor/client
node scripts/check-erd-card-containment.ts
node scripts/check-erd-group-label.ts
```

Expected: both pass unchanged. They are the control that proves the change did not disturb the card's contour or the specialization label.

## 4. The graph and the payload still carry every value

```bash
.venv/bin/pytest packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py -q
.venv/bin/pytest packages/aoa-maxitor/tests/test_list_entities_payload_dictionary.py -q
```

Expected: both pass. They run unchanged, which is the statement "the JSON graph passes everything" and "the payload is not narrowed".

## 5. The adversarial pair

Each break is introduced alone, the named check is run, and the edit is reverted.

```bash
# (a) a value row comes back: the dictionary check must fail, the graph test must pass
#     restore the valueRows block in client/src/lib/buildDotSource.ts
cd packages/aoa-maxitor/client && node scripts/check-erd-dictionary-values.ts   # expect failure
cd ../../.. && .venv/bin/pytest packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py -q  # expect pass

# (b) the export loses the values: the graph test must fail, the dictionary check must pass
#     comment out the properties["values"] assignment at EntityGraphNode line 93
.venv/bin/pytest packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_reference_json.py -q  # expect failure
cd packages/aoa-maxitor/client && node scripts/check-erd-dictionary-values.ts   # expect pass
```

The same pair exists for the payload (`list_entities_action.py:370`, where `entity["values"]` is built): emptying it must fail `test_list_entities_payload_dictionary.py` while the dictionary check stays green.

## 6. The drawing is readable again (visual proof)

Against a running Maxitor on `127.0.0.1:8000` with the model loaded from `https://admingameoffer.aoa.run/graph-json`:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --virtual-time-budget=20000 --dump-dom \
  "http://127.0.0.1:8000/?source=https%3A%2F%2Fadmingameoffer.aoa.run%2Fgraph-json&view=domain-erd&domain=datamodel.players.players_domain.PlayersDomain" \
  | grep -o 'viewBox="0.00 0.00 [0-9.]* [0-9.]*"'
```

| Model state | Expected `viewBox` height |
| --- | --- |
| before the change (measured 2026-10-25) | `6800` |
| after the change (measured 2026-10-25) | `2075` for the players domain; `1423`, `1242` and `1667` for events, offers and showcases; `2777` for the all-domains view |
| any dictionary card | no green value block; the card is its header and its field rows |

The headless binary may be any Chromium build; what matters is the `viewBox` of the Graphviz SVG. Repeat the render for the other three domains (`EventsDomain`, `OffersDomain`, `ShowcasesDomain`) and once without `domain=` for the all-domains view; in each of them the seven dictionaries must contribute no value row at all — that walk is what SC-002 counts.

## 7. The closing run

```bash
bash scripts/run_checks_with_log.sh
```

Expected: exits clean. The Vite chunk-size advisory and the LangGraph pending-deprecation warning remain in the log and are not acted on (constitution, final section). The script runs all three client checks, so a stale assertion is caught here even if it was skipped locally.
