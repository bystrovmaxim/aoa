// src/rooms/initials.test.ts
import { describe, expect, it } from "vitest";
import { initials, inkOn } from "@/rooms/initials";

describe("initials", () => {
  it("takes the first letters of the first two words", () => {
    expect(initials("Vera Ilina")).toBe("VI");
    expect(initials("  egor   sokolov  petrovich ")).toBe("ES");
  });

  it("takes the first two letters of a single word", () => {
    expect(initials("Anna")).toBe("AN");
    expect(initials("b")).toBe("B");
  });

  it("keeps letters outside the Latin alphabet whole", () => {
    expect(initials("Антон Быстров")).toBe("АБ");
    expect(initials("😀Smile")).toBe("😀S");
  });

  it("shows a question mark for an empty name", () => {
    expect(initials("   ")).toBe("?");
  });
});

describe("inkOn", () => {
  it("writes white on dark fills and dark on light ones", () => {
    expect(inkOn("#4338ca")).toBe("#ffffff");
    expect(inkOn("#fde047")).toBe("#0f172a");
  });
});
