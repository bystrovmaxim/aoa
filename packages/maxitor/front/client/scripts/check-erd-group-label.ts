/** Verify that a specialization group names its dictionary once, from the server's payload. */
import assert from "node:assert/strict";
import { buildDotSource } from "../src/lib/buildDotSource.ts";

const entities = [
  { id: "shop.FirstSpecEntity", label: "FirstSpecEntity", fields: [] },
  { id: "shop.RepressSpecEntity", label: "RepressSpecEntity", fields: [] },
];

const group = {
  group_id: "shop:kind",
  label: "kind (by EditionKindEnumEntity)",
  classifier_field: null,
  members: ["shop.FirstSpecEntity", "shop.RepressSpecEntity"],
};

const modern = buildDotSource({ entities, relations: [], groups: [group] }, "gv-dot-lr");
const modernCount = modern.split("EditionKindEnumEntity").length - 1;
assert.equal(modernCount, 1, `the dictionary name appears ${modernCount} times`);
assert.ok(
  modern.includes('label="kind (by EditionKindEnumEntity)"'),
  "the server's label was not rendered as received",
);

// A stale producer may still send the dictionary name beside the label; the client must not
// append it a second time.
const staleGroup = { ...group, dictionary_label: "EditionKindEnumEntity" };
const stale = buildDotSource({ entities, relations: [], groups: [staleGroup] }, "gv-dot-lr");
const staleCount = stale.split("EditionKindEnumEntity").length - 1;
assert.equal(staleCount, 1, `a stale dictionary_label produced ${staleCount} names`);

// The escaping of the label happens once, before the renderer.
const escaped = buildDotSource(
  { entities, relations: [], groups: [{ ...group, label: "kind (by A&B)" }] },
  "gv-dot-lr",
);
assert.ok(escaped.includes('label="kind (by A&amp;B)"'), "the label was not escaped exactly once");

console.log("Group label: composed once, rendered as received");
