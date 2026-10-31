// src/lib/stepKeys.test.ts
import { describe, expect, it } from "vitest";
import { changeStepOfKey, stepOfKey } from "./stepKeys";

const press = (key: string, extra: Partial<KeyboardEvent> = {}, target: Element = document.body) =>
  stepOfKey({ key, shiftKey: true, altKey: false, ctrlKey: false, metaKey: false, target, ...extra } as unknown as KeyboardEvent);

describe("Shift + ← → on the page (spec 038)", () => {
  it("step one older and one newer", () => {
    expect(press("ArrowLeft")).toBe(-1);
    expect(press("ArrowRight")).toBe(1);
  });

  it("ask for nothing without Shift, with another modifier, or on another key", () => {
    expect(press("ArrowLeft", { shiftKey: false })).toBeNull();
    expect(press("ArrowRight", { metaKey: true })).toBeNull();
    expect(press("ArrowUp")).toBeNull();
  });

  it("leave the keys to a field one types in and to a track's handle", () => {
    const input = document.createElement("input");
    const handle = document.createElement("div");
    handle.setAttribute("role", "slider");
    const inside = document.createElement("span");
    handle.appendChild(inside);
    expect(press("ArrowLeft", {}, input)).toBeNull();
    expect(press("ArrowRight", {}, inside)).toBeNull();
  });
});

describe("the keys that step through changes", () => {
  const press = (key: string, more: object = {}) => ({ key, shiftKey: true, altKey: false, ctrlKey: false, metaKey: false, target: null, ...more });

  it("are Shift with up and down", () => {
    expect(changeStepOfKey(press("ArrowUp"))).toBe(-1);
    expect(changeStepOfKey(press("ArrowDown"))).toBe(1);
  });

  it("are not the keys of versions, nor the arrows alone", () => {
    expect(changeStepOfKey(press("ArrowLeft"))).toBeNull();
    expect(changeStepOfKey(press("ArrowDown", { shiftKey: false }))).toBeNull();
  });
});
