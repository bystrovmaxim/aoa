// src/lib/fieldTypeLabel.test.ts
import { describe, expect, it } from "vitest";
import { buildDotSource, cleanFieldType, fitFieldType, FIELD_TYPE_MAX_CHARS } from "@/lib/buildDotSource";

describe("a field type from an older service reads as one clean name (spec 029, FR-031)", () => {
  it.each([
    ["str", "str"],
    ["UnionType[str, NoneType]", "str | None"],
    ["Union[str, NoneType]", "str | None"],
    ["Optional[str]", "str | None"],
    ["UnionType[NoneType, int]", "int | None"],
    ["UnionType[int, str]", "int | str"],
    ["AssociationOne[CurrencyEnumEntity]", "CurrencyEnumEntity"],
    ["CompositeMany[LineCoreEntity]", "LineCoreEntity[]"],
    ["UnionType[AssociationOne[CurrencyEnumEntity], NoneType]", "CurrencyEnumEntity | None"],
    ["Generalization[GeneralizationHeadCoreEntity]", "GeneralizationHeadCoreEntity"],
    ["Specialization[Union[GeneralizationVariantASpecEntity, GeneralizationVariantBSpecEntity], GeneralizationShapesKindEnumEntity]", "GeneralizationVariantASpecEntity | GeneralizationVariantBSpecEntity"],
    ["list[str]", "str[]"],
    ["frozenset[int]", "int[]"],
    ["tuple[int, ...]", "int[]"],
    ["tuple[int, str]", "tuple[int, str]"],
    ["dict[str, UnionType[int, NoneType]]", "dict[str, int | None]"],
    ["Literal[a, b]", '"a" | "b"'],
    ["Literal[1, 2]", "1 | 2"],
  ])("%s → %s", (raw, clean) => {
    expect(cleanFieldType(raw)).toBe(clean);
  });

  it.each(["str | None", "CurrencyEnumEntity", "LineCoreEntity[]", '"a" | "b"', "dict[str, int | None]", "A (x) | B (y)"])(
    "leaves a clean name as it is: %s",
    (clean) => {
      expect(cleanFieldType(clean)).toBe(clean);
      expect(cleanFieldType(cleanFieldType(clean))).toBe(clean);
    },
  );

  it("cuts a name too long for the column with …", () => {
    const long = "VeryLongEntityNameThatDoesNotFitTheTypeColumnCoreEntity";
    expect(fitFieldType(long)).toHaveLength(FIELD_TYPE_MAX_CHARS);
    expect(fitFieldType(long).endsWith("…")).toBe(true);
    expect(fitFieldType("str")).toBe("str");
  });
});

describe("an ERD row's type cell (spec 029, FR-030)", () => {
  it("shows the clean name and keeps the full annotation in its tooltip", () => {
    const dot = buildDotSource(
      {
        entities: [
          { id: "shop.PlayerCoreEntity", label: "PlayerCoreEntity", color: "#16a34a", entity_kind: "core", fields: [{ name: "region", type: "UnionType[str, NoneType]", annotation: "UnionType[str, NoneType]" }] },
        ],
        relations: [],
      },
      "gv-dot-lr",
    );
    expect(dot).toContain(">str | None</FONT>");
    expect(dot).toContain('TOOLTIP="UnionType[str, NoneType]"');
  });
});
