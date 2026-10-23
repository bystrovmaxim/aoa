/** Verify that a dictionary card prints labels and keeps the code in a tooltip. */
import assert from "node:assert/strict";
import { Graphviz } from "@hpcc-js/wasm-graphviz";
import { buildDotSource } from "../src/lib/buildDotSource.ts";

const dot = buildDotSource({
  entities: [
    {
      id: "shop.RichEnumEntity",
      label: "RichEnumEntity",
      // The payload hands the card no field rows for a dictionary: dropping them is the
      // action's job, and the renderer names no dictionary field of its own.
      fields: [],
      values: [
        {
          code: "eur",
          display_name: "Euro",
          properties: [
            { name: "symbol", value: "€" },
            { name: "note", value: "<safe> & readable" },
          ],
        },
        { code: "tagged", display_name: "Tagged", properties: [{ name: "tags", value: '["a", "b"]' }] },
        { code: "empty", display_name: "Empty", properties: [] },
        { code: "amp&code", display_name: "Ampersand", properties: [] },
      ],
    },
    {
      id: "shop.PriceTagCoreEntity",
      label: "PriceTagCoreEntity",
      fields: [{ name: "amount", type: "float", primary_key: false, foreign_key: false }],
    },
  ],
  relations: [],
}, "gv-dot-lr");

assert.ok(dot.includes("symbol: €"), "Dictionary properties were dropped");
assert.ok(dot.includes("&lt;safe&gt; &amp; readable"), "Property text was not escaped");
assert.ok(
  dot.includes("tags: [&quot;a&quot;, &quot;b&quot;]"),
  "An array property was not rendered as its JSON text",
);
assert.equal(
  (dot.match(/<BR ALIGN="LEFT"\/>/g) || []).length,
  3,
  "A value with no properties drew a row of its own",
);

// The label is printed; the code is not, anywhere the reader can see it as text.
assert.ok(dot.includes(">Euro<"), "The label is no longer printed");
assert.ok(!dot.includes(">eur<"), "The code is printed as a cell of its own");
// The code survives on the row as a tooltip, escaped exactly like every other text.
assert.ok(dot.includes('TOOLTIP="code: eur"'), "The code is not carried as a tooltip");
assert.ok(
  dot.includes('TOOLTIP="code: amp&amp;code"'),
  "A code needing escaping is not escaped in the tooltip",
);

// A non-dictionary entity keeps every row it had.
assert.ok(dot.includes(">amount<"), "A plain entity lost its field row");

const svg = (await Graphviz.load()).layout(dot, "svg", "dot");
assert.ok(svg.includes("symbol: €"), "Graphviz did not render the property");
assert.ok(svg.includes("&lt;safe&gt; &amp; readable"), "The rendered SVG lost the escaped note");
assert.ok(
  svg.includes("tags: [&quot;a&quot;, &quot;b&quot;]"),
  "Graphviz did not render the array property's JSON text",
);
assert.ok(svg.includes('xlink:title="code: eur"'), "The rendered SVG lost the code tooltip");
assert.ok(
  !svg.includes(">eur<"),
  "The rendered SVG prints the code, so the tooltip is decorative rather than the only place it lives",
);
console.log("Dictionary card: labels printed, codes carried as tooltips, everything escaped");
