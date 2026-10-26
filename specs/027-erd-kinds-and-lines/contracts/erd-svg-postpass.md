# Contract: what the ERD post-pass relies on in the Graphviz SVG

Owner: Maxitor client, `src/lib/buildDotSource.ts` (writes it) and `src/lib/erdPostPass.ts` (reads it). Checked by `scripts/check-erd-kinds-and-lines.ts` on the client's own WASM Graphviz.

## Addressable cells

Graphviz emits an element id for an HTML-label cell only when the cell has `ID` **and** `TOOLTIP` (or `HREF`). The emitted element is `<g id="a_<cell-ID>"><a xlink:title="<tooltip>">` around the cell's `<polygon>` fill (only if the cell has a `BGCOLOR`) and its `<text>`. The node's name is **not** part of the id, so every cell `ID` carries the table's index *i* (its position in the drawn entity list) and is unique across the drawing.

| Cell | `ID` | `TOOLTIP` | fill |
|---|---|---|---|
| header (the one coloured cell) | `hd<i>` | the table's name | domain colour |
| header kind slot | `ks<i>` | the kind's display name | domain colour, so its box is emitted |
| header name | `hn<i>` | `Click to copy` | domain colour, so its box is emitted |
| field name of row *n* | `fn<i>_<n>` | `Click to copy` | the row tint |
| type of row *n* | `ft<i>_<n>` | the type text | the row tint |

Row index *n* is the row's position in `fields`; the post-pass maps (table, field name) → every *n* with that name (own row and FK row).

## Header

```
<TD COLSPAN="3" BGCOLOR="<domain>" ALIGN="CENTER" WIDTH="210" ID="hd<i>" TOOLTIP="<table name>">
  <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR>
    <TD ID="ks<i>" TOOLTIP="<kind label>" BGCOLOR="<domain>" WIDTH="13" HEIGHT="13" FIXEDSIZE="TRUE"></TD>
    <TD WIDTH="4"></TD>
    <TD ID="hn<i>" TOOLTIP="Click to copy" BGCOLOR="<domain>"><FONT COLOR="white" POINT-SIZE="12"><B><name></B></FONT></TD>
  </TR></TABLE>
</TD>
```

The header remains one coloured cell; `containNodeFills.ts` rounds it. Graphviz spreads the header's extra width over the three inner cells and centres the name in its own cell, so the slot does not sit next to the name by itself. The post-pass (`placeKindIcons`) reads the `hd`, `ks` and `hn` boxes, takes the name's width as `left + right − 2·x` of the `hn` box and text, centres *icon + 4 pt + name* in the header, moves the name's `x`, and draws the white glyph (13 pt, from `ks`'s top) inside the `ks` link so its tooltip covers it.

## Edges

- Association and reference edges: `dir=both`, `arrowhead`/`arrowtail` ∈ {`tee`, `crow`}, `headlabel` = `source_field`, `taillabel` = `target_field` (or none), no `label`.
- Generalization: `arrowhead=empty`, unchanged.
- The post-pass adds one transparent hit path (class `erd-hit`) per `g.edge`, sets `data-src`, `data-tgt`, `data-sf`, `data-tf` on the group from the payload, and toggles class `is-hovered` on hover.

## Marks and copy

- Marking a row sets `font-weight="bold"` and `fill` (`#0f172a` name, `#334155` type) on the `<text>` inside `fn_<n>` / `ft_<n>`; removing it restores the original attributes. No `<polygon>` changes.
- Hovering `fn_<n>` or `ft_<n>` of a field that is a `source_field` or `target_field` of one or more edges (or a key row, for edges without a `target_field` pointing at its table) adds `is-hovered` to every such edge, raises each, and marks the rows at their ends; leaving the row removes it all.
- A click on `hn` or `fn_<n>` copies that cell's text; a press moving more than 4 px does not.
