// src/lib/pageSettings.test.ts
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PageSettingsProvider, clearLocalPageSettings, keepRoomSettings, ownSettingsByPage, usePageSetting, type RoomSettings } from "@/lib/pageSettings";
import { HalfProvider, type Half } from "@/lib/half";
import { seedMessages } from "@/rooms/seed";

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

  it("never show the person's own value, so everyone in the room sees one picture (spec 029)", () => {
    const own = layoutOn(ERD);
    act(() => own.result.current[1]("gv-neato"));
    const view = layoutOn(ERD, { settings: {}, set: vi.fn() });
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

describe("seeding a room the tab opens (spec 029)", () => {
  it("collects the tab's own values by page", () => {
    const erd = layoutOn(ERD);
    const players = layoutOn(ERD_PLAYERS);
    act(() => erd.result.current[1]("gv-neato"));
    act(() => players.result.current[1]("gv-circo"));
    expect(ownSettingsByPage()).toEqual({ [ERD]: { layout: "gv-neato" }, [ERD_PLAYERS]: { layout: "gv-circo" } });
  });

  it("sends one setting per message", () => {
    const messages = seedMessages({ [ERD]: { layout: "gv-neato", one_hop: false } });
    expect(messages).toEqual([
      { type: "seed", page: ERD, settings: { layout: "gv-neato" } },
      { type: "seed", page: ERD, settings: { one_hop: false } },
    ]);
  });

  it("leaves out a value too large for one room message", () => {
    const long = Array.from({ length: 80 }, (_, i) => `entity-${"x".repeat(50)}-${i}`);
    const messages = seedMessages({ [ERD]: { layout: "gv-neato", disabled_entities: long } });
    expect(messages).toEqual([{ type: "seed", page: ERD, settings: { layout: "gv-neato" } }]);
  });
});

describe("page settings in a half", () => {
  const half = (side: "a" | "b"): Half => ({ side, read: { source: side, key: "" }, name: side });

  /** Render a setting on the ERD as half ``side`` sees it. */
  function inHalf(side: "a" | "b", name: string, fallback: unknown, room: RoomSettings | null = null) {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <PageSettingsProvider page={ERD} room={room}>
        <HalfProvider half={half(side)}>{children}</HalfProvider>
      </PageSettingsProvider>
    );
    return renderHook(() => usePageSetting(name, fallback), { wrapper });
  }

  it("give each half its own layout mode, starting from the page's", () => {
    const page = layoutOn(ERD);
    act(() => page.result.current[1]("gv-neato"));
    const [a, b] = [inHalf("a", "layout", "gv-dot-lr"), inHalf("b", "layout", "gv-dot-lr")];
    expect(a.result.current[0]).toBe("gv-neato");
    act(() => a.result.current[1]("gv-circo"));
    expect(a.result.current[0]).toBe("gv-circo");
    expect(b.result.current[0]).toBe("gv-neato");
    expect(layoutOn(ERD).result.current[0]).toBe("gv-neato");
  });

  it("share every other setting between the halves", () => {
    const [a, b] = [inHalf("a", "one_hop", false), inHalf("b", "one_hop", false)];
    act(() => a.result.current[1](true));
    expect(b.result.current[0]).toBe(true);
  });

  it("send a half's layout mode to the room under its own name", () => {
    const set = vi.fn();
    const a = inHalf("a", "layout", "gv-dot-lr", { settings: {}, set });
    act(() => a.result.current[1]("gv-neato"));
    expect(set).toHaveBeenCalledWith(ERD, "layout_a", "gv-neato");
  });
});
