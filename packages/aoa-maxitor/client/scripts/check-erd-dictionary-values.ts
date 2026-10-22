/** Verify that dictionary descriptions reach the rendered card as escaped text. */
import assert from "node:assert/strict";
import { Graphviz } from "@hpcc-js/wasm-graphviz";
import { buildDotSource } from "../src/lib/buildDotSource.ts";

const dot = buildDotSource({
  entities: [{
    id: "shop.CurrencyEnumEntity", label: "CurrencyEnumEntity", fields: [],
    values: [{ code: "eur", display_name: "Euro", properties: [
      { name: "symbol", value: "€" },
      { name: "note", value: "<safe> & readable" },
    ] }],
  }],
  relations: [],
}, "gv-dot-lr");
assert.ok(dot.includes("symbol: €"), "Dictionary properties were dropped");
assert.ok(dot.includes("&lt;safe&gt; &amp; readable"), "Property text was not escaped");
const svg = (await Graphviz.load()).layout(dot, "svg", "dot");
assert.ok(svg.includes("symbol: €"), "Graphviz did not render the property");
console.log("Dictionary card: properties preserved, escaped and rendered");
