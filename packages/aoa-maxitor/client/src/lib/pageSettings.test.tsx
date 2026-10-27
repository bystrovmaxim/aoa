// src/lib/pageSettings.test.ts
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PageSettingsProvider, clearLocalPageSettings, keepRoomSettings, usePageSetting, type RoomSettings } from "@/lib/pageSettings";

const ERD = "view=domain-erd";
const ERD_PLAYERS = "view=domain-erd&domain=players";

afterEach(() => clearLocalPageSettings());

/** Render ``usePageSetting("layout", "gv-dot-lr")`` on ``page``, optionally in a room. */
function layoutOn(page: string, room: RoomSettings | null = null) {
  let current = { page, room };
  const wrapper = ({ children }: { children: ReactNode }) => (
    <PageSettingsProvider page={current.page} room={current.room}>
      {children}
    </PageSettingsProvider>
  );
  const hook = renderHook(() => usePageSetting("layout", "gv-dot-lr"), { wrapper });
  return {
    ...hook,
    move(next: { page?: string; room?: RoomSettings | null }) {
      current = { ...current, ...next };
      hook.rerender();
    },
  };
}

describe("page settings outside a room", () => {
  it("keep a value per page for the life of the tab", () => {
    const first = layoutOn(ERD);
    act(() => first.result.current[1]("gv-neato"));
    expect(first.result.current[0]).toBe("gv-neato");
    first.unmount();
    expect(layoutOn(ERD).result.current[0]).toBe("gv-neato");
  });

  it("keep two pages apart", () => {
    const erd = layoutOn(ERD);
    act(() => erd.result.current[1]("gv-circo"));
    expect(layoutOn(ERD_PLAYERS).result.current[0]).toBe("gv-dot-lr");
  });
});

describe("page settings inside a room", () => {
  it("send one setting with the new value and show the room's", () => {
    const set = vi.fn();
    const room: RoomSettings = { settings: {}, set };
    const view = layoutOn(ERD, room);
    act(() => view.result.current[1]("gv-fdp"));
    expect(set).toHaveBeenCalledTimes(1);
    expect(set).toHaveBeenCalledWith(ERD, "layout", "gv-fdp");
    // Someone else's change arrives later and wins.
    view.move({ room: { settings: { [ERD]: { layout: "gv-circo" } }, set } });
    expect(view.result.current[0]).toBe("gv-circo");
  });

  it("give a newcomer the room's value for the page", () => {
    const view = layoutOn(ERD, { settings: { [ERD]: { layout: "gv-dot-tb" } }, set: vi.fn() });
    expect(view.result.current[0]).toBe("gv-dot-tb");
  });

  it("are untouched by a value for another page", () => {
    const view = layoutOn(ERD, { settings: { [ERD_PLAYERS]: { layout: "gv-neato" } }, set: vi.fn() });
    expect(view.result.current[0]).toBe("gv-dot-lr");
  });

  it("stay as they were after leaving the room", () => {
    const settings = { [ERD]: { layout: "gv-circo" } };
    const view = layoutOn(ERD, { settings, set: vi.fn() });
    act(() => keepRoomSettings(settings));
    view.move({ room: null });
    expect(view.result.current[0]).toBe("gv-circo");
  });
});

describe("the default value", () => {
  it("is the same object on every render, so effects depending on it stay quiet", () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <PageSettingsProvider page={ERD} room={null}>
        {children}
      </PageSettingsProvider>
    );
    const view = renderHook(() => usePageSetting<string[]>("disabled_kinds", []), { wrapper });
    const first = view.result.current[0];
    view.rerender();
    expect(view.result.current[0]).toBe(first);
  });
});
