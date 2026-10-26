/**
 * Verify that a dictionary card draws no value row.
 *
 * The card is a dictionary's entity card: its header, its own field rows and the arrows
 * that reach it. A declared value is carried by the payload and by the graph, not by the
 * drawing — so no label, no property and no code may reach the DOT or the SVG, and the
 * card may not depend on how many values the dictionary declares.
 */
import assert from "node:assert/strict";
import { Graphviz } from "@hpcc-js/wasm-graphviz";
import { buildDotSource, type ErdValue } from "../src/lib/buildDotSource.ts";

const dot = buildDotSource({
  entities: [
    {
      id: "shop.RichEnumEntity",
      label: "RichEnumEntity",
      // A dictionary card keeps its own fields — the kind's `code`/`display_name` rows are
      // dropped by the action, but a declared field such as `is_obsolete` is still a row.
      fields: [{ name: "is_obsolete", type: "bool", primary_key: false, foreign_key: false }],
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
    {
      id: "shop.OfferCoreEntity",
      label: "OfferCoreEntity",
      fields: [
        {
          name: "region",
          type: "RichEnumEntity",
          primary_key: false,
          foreign_key: false,
          reference_qualname: "shop.RichEnumEntity",
        },
      ],
    },
  ],
  relations: [
    {
      source: "shop.OfferCoreEntity",
      target: "shop.RichEnumEntity",
      label: "region",
      relationship_kind: "reference",
      source_cardinality: "one",
      target_cardinality: "zero_many",
    },
  ],
}, "gv-dot-lr");

// No value reaches the DOT: not its label, not its properties, not its code.
assert.ok(!dot.includes(">Euro<"), "A value label is printed on the card");
assert.ok(!dot.includes(">Tagged<"), "A value label is printed on the card");
assert.ok(!dot.includes(">Empty<"), "A value label is printed on the card");
assert.ok(!dot.includes(">Ampersand<"), "A value label is printed on the card");
assert.ok(!dot.includes("symbol: €"), "A value property is printed on the card");
assert.ok(!dot.includes("&lt;safe&gt;"), "A value property is printed on the card");
assert.ok(!dot.includes("tags: ["), "An array property is printed on the card");
assert.ok(
  !dot.includes('<BR ALIGN="LEFT"/>'),
  "Something draws a line inside a value row that should not exist",
);

// The code does not survive anywhere: the row that carried the tooltip is gone with it.
assert.ok(!dot.includes('TOOLTIP="code:'), "The code tooltip survived the row it belonged to");
assert.ok(!dot.includes("code: eur"), "The code is carried as text");

// The dictionary's own field rows are still drawn.
assert.ok(dot.includes(">is_obsolete<"), "The dictionary lost its own field row");
assert.ok(dot.includes(">bool<"), "The dictionary field lost its type");

// A non-dictionary entity keeps every row it had.
assert.ok(dot.includes(">amount<"), "A plain entity lost its field row");

// The reference is one arrow to the dictionary, labelled with the field, and the row
// keeps the dictionary name as its type — with no "→ name" after it (spec 027, FR-031):
// the line already says what the field references.
assert.ok(
  dot.includes('"shop.OfferCoreEntity" -> "shop.RichEnumEntity"'),
  "The reference edge is not drawn",
);
assert.ok(dot.includes('label="region"'), "The reference edge lost its field label");
assert.ok(!dot.includes("→"), "A type cell repeats the line with a → suffix");
assert.equal(
  (dot.match(/<I>RichEnumEntity<\/I>/g) || []).length,
  1,
  "The row does not name the dictionary exactly once as its type",
);

// A graph saved before the change carries only reference_qualname: it still renders, and
// the row still names the dictionary, with no arrow invented for a relation it lacks.
const legacyDot = buildDotSource({
  entities: [
    {
      id: "shop.RichEnumEntity",
      label: "RichEnumEntity",
      fields: [],
      values: [{ code: "eur", display_name: "Euro", properties: [] }],
    },
    {
      id: "shop.LegacyOfferCoreEntity",
      label: "LegacyOfferCoreEntity",
      fields: [
        {
          name: "region",
          type: "RichEnumEntity",
          primary_key: false,
          foreign_key: false,
          reference_qualname: "shop.RichEnumEntity",
        },
      ],
    },
  ],
  relations: [],
}, "gv-dot-lr");
assert.ok(legacyDot.includes("<I>RichEnumEntity</I>"), "A legacy graph's row no longer names its dictionary");
assert.ok(!legacyDot.includes("→"), "A legacy graph's type cell carries a → suffix");
assert.ok(
  !legacyDot.includes('"shop.LegacyOfferCoreEntity" ->'),
  "A legacy graph invented an edge it does not carry",
);

// The drawing may not depend on how many values are declared: the specification names one,
// three, twenty-six and ninety-three, and zero must look the same as all of them.
const valuesFor = (count: number): ErdValue[] =>
  Array.from({ length: count }, (_, index) => ({
    code: `code-${index}`,
    display_name: `Value ${index}`,
    properties: [{ name: "is_obsolete", value: "false" }],
  }));

const dictionaryDot = (values: ErdValue[]): string =>
  buildDotSource(
    {
      entities: [
        {
          id: "shop.RichEnumEntity",
          label: "RichEnumEntity",
          fields: [{ name: "is_obsolete", type: "bool", primary_key: false, foreign_key: false }],
          values,
        },
      ],
      relations: [],
    },
    "gv-dot-lr",
  );

const withoutValues = dictionaryDot([]);
for (const count of [0, 1, 3, 26, 93]) {
  assert.equal(
    dictionaryDot(valuesFor(count)),
    withoutValues,
    `A dictionary with ${count} values draws a different card than one with none`,
  );
}

// The golden of an ordinary card: it must be byte-identical, not merely still present. First
// recorded in specs/022-erd-without-dictionary-values/evidence/baseline.md; re-recorded for
// specs/027-erd-kinds-and-lines, which changes every card on purpose — the 210 pt minimum width,
// the kind icon slot before the name, addressable cells, and types on the right edge.
const PRICE_TAG_GOLDEN: string = [
  "digraph ERD {",
  '  graph [rankdir=LR fontname="Helvetica" bgcolor=transparent pad="0.5" nodesep="0.8" ranksep="1.2"]',
  '  node  [shape=none fontname="Helvetica" fontsize=11 margin="0"]',
  '  edge  [fontname="Helvetica" fontsize=9 color="#94a3b8" arrowsize=0.7]',
  "",
  '  "shop.PriceTagCoreEntity" [label=<<TABLE BGCOLOR="white" BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="ROUNDED" COLOR="#3b82f6"><TR><TD COLSPAN="3" BGCOLOR="#3b82f6" ALIGN="CENTER" WIDTH="210" ID="hd0" TOOLTIP="PriceTagCoreEntity"><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR><TD ID="ks0" TOOLTIP="Unknown" BGCOLOR="#3b82f6" WIDTH="13" HEIGHT="13" FIXEDSIZE="TRUE"></TD><TD WIDTH="4"></TD><TD ID="hn0" TOOLTIP="Click to copy" BGCOLOR="#3b82f6"><FONT COLOR="white" POINT-SIZE="12"><B>PriceTagCoreEntity</B></FONT></TD></TR></TABLE></TD></TR><TR><TD BGCOLOR="#ffffff" WIDTH="28"></TD><TD BGCOLOR="#ffffff" ALIGN="LEFT" ID="fn0_0" TOOLTIP="Click to copy">amount</TD><TD BGCOLOR="#ffffff" ALIGN="RIGHT" ID="ft0_0" TOOLTIP="float"><FONT COLOR="#64748b"><I>float</I></FONT></TD></TR></TABLE>>]',
  "",
  "}",
].join("\n");

const priceTagDot = buildDotSource(
  {
    entities: [
      {
        id: "shop.PriceTagCoreEntity",
        label: "PriceTagCoreEntity",
        fields: [{ name: "amount", type: "float", primary_key: false, foreign_key: false }],
      },
    ],
    relations: [],
  },
  "gv-dot-lr",
);
assert.equal(priceTagDot, PRICE_TAG_GOLDEN, "An ordinary card changed against the recorded golden");

const svg = (await Graphviz.load()).layout(dot, "svg", "dot");
assert.ok(!svg.includes("Euro"), "The rendered SVG prints a value label");
assert.ok(!svg.includes("symbol: €"), "The rendered SVG prints a value property");
assert.ok(!svg.includes("tags: ["), "The rendered SVG prints an array property");
assert.ok(!svg.includes('xlink:title="code:'), "The rendered SVG carries the code tooltip");
assert.ok(svg.includes(">region<"), "The rendered SVG lost the reference edge label");
assert.ok(svg.includes(">is_obsolete<"), "The rendered SVG lost the dictionary field row");
assert.ok(!svg.includes(">eur<"), "The rendered SVG prints a value code");

console.log("Dictionary card: no value row, its own fields and the reference intact");
