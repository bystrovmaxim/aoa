# Data Model: Side by Side

## Half (client)

| Field | Meaning |
|-------|---------|
| `side` | `a` or `b` |
| `read` | the version's source and key |
| `name` | the version's name, for "Not in …" |
| `otherSide` | what the other half is, for the locator |

Own: pan, zoom, layout mode, surface. Absent outside Side by side.

## Selection (page setting `selected`)

`{ kind: "node" | "row" | "edge" | "table", id } | null`. Cleared by empty space or Escape. Not in the address.

## View

`one | diff | split`. Address: `mode=split` with `a` and `b`. `split` needs `a`. On a phone `split` is shown as A / B; which side is flipped to is personal.

## Page settings added

| Name | Value |
|------|-------|
| `layout_a`, `layout_b` | the layout mode of a half |
| `selected` | as above |

## Room (server)

`Room.view: str = "one"`, in `snapshot()`. Invariant: `view == "split"` or `"diff"` only with `version_a`; `one` only without it.

## Locator result

`in_view | moved | hidden | absent`: `moved` glides and says so; `hidden` says the filters hide it; `absent` says "Not in <name>".
