/** Verify that dictionary descriptions reach the rendered card as escaped text. */
import assert from "node:assert/strict";
import { Graphviz } from "@hpcc-js/wasm-graphviz";
import { buildDotSource } from "../src/lib/buildDotSource.ts";

const dot = buildDotSource({
  entities: [{
    id: "shop.RichEnumEntity", label: "RichEnumEntity", fields: [],
    values: [
      {
        code: "eur", display_name: "Euro", properties: [
          { name: "symbol", value: "€" },
          { name: "note", value: "<safe> & readable" },
        ],
      },
      { code: "tagged", display_name: "Tagged", properties: [{ name: "tags", value: '["a", "b"]' }] },
      { code: "empty", display_name: "Empty", properties: [] },
    ],
  }],
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

const svg = (await Graphviz.load()).layout(dot, "svg", "dot");
assert.ok(svg.includes("symbol: €"), "Graphviz did not render the property");
assert.ok(svg.includes("&lt;safe&gt; &amp; readable"), "The rendered SVG lost the escaped note");
assert.ok(
  svg.includes("tags: [&quot;a&quot;, &quot;b&quot;]"),
  "Graphviz did not render the array property's JSON text",
);
console.log("Dictionary card: properties preserved, escaped and rendered");
