# Contract: the screen in Diff

## Address bar

`?history=<name>&mode=diff&a=<sha>&b=<sha|live>&view=domain-erd&domain=…#key=…` — `mode` absent in One; `a` only in Diff. A reversed pair opens swapped and the bar is corrected.

## Mode switch

| Mode of the history | One | Diff | Side by side |
|---|---|---|---|
| M2, M4, M5 | on/off | on/off | greyed, "comes later" |
| M3, M6 (one point) | on | greyed, "needs two versions" | greyed, "comes later" |
| M1, M7 | no switch | | |

## Version button

| State | Text |
|---|---|
| One | as spec 037 (`◷ 0.11.0 · #147 ▾`) |
| Diff on the ERD, changes | `◷ A 0.8.0 → B 0.9.0  +15 −1 ~3 ▾` — each count in its colour |
| Diff on the ERD, nothing changed | `◷ A 0.8.0 → B 0.9.0  no changes ▾` |
| Diff on another diagram (until #291–#293) | `◷ A 0.8.0 → B 0.9.0 ▾` |
| Phone | `A 0.8.0 → B 0.9.0 +15 −1 ~3`, names shortened first |

## Track in Diff

Two handles, chips in their handle's style (`A 0.8.0`, `B 0.9.0`), the stretch between dark. Keys: ← → move the focused handle (past the other, roles swap, focus stays); Shift + ← → both; Home/End the focused one. Handles are named to assistive technology by role ("A, 0.8.0, older version").

## Under the track

```text
┌ A · 0.8.0 · #128 ───────────┐ ┌ B · 0.9.0 · #129 ───────────┐
│ message, ≤ 9 lines, scrolls │ │ message, ≤ 9 lines, scrolls │
└─────────────────────────────┘ └─────────────────────────────┘
▸ 3 versions between
   #127  Offer request log — first line…
```

Live as B: B's box holds Live's closing line. A phone stacks A over B.

## ERD marks

| Status | Table | Row | Line |
|---|---|---|---|
| added | green frame and header, `+` | green tint, `+` | green |
| removed | red, dashed frame, `−` | red tint, `−`, name struck through | red, dashed |
| changed | amber frame, `~` (only when the table's own properties changed) | amber tint, `~`; type `~~old~~ → new` when it fits | amber; retargeted: solid to B's target, thin dashed to A's |
| unchanged | faded | faded | faded |

"No changes": drawn as in One, nothing faded.

## Card

Opened by a click on a marked table or row; closed by a click outside or Escape.

```text
~ chosen_offer                       changed
target_id   OfferCoreEntity
            → OfferRequestItemDetailEntity
properties.description   "The offer …" → "The chosen offer …"
```

Added/removed: one line, "Added in 0.9.0" / "Removed in 0.9.0". Values are text, never HTML.

## Left panel

Pages of A and B together; `+` beside a page only in B, `−` beside one only in A.
