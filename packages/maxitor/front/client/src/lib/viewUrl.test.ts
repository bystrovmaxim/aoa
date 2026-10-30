// src/lib/viewUrl.test.ts
import { afterEach, describe, expect, it } from "vitest";
import { clearLocalPageSettings, seedPageSettings, shownPageSettings } from "@/lib/pageSettings";
import { setUrlView, syncUrlToState } from "@/lib/urlState";
import { cameraToParams, paramsToCamera, paramsToView, viewToParams } from "./viewUrl";

afterEach(() => {
  clearLocalPageSettings();
  setUrlView({});
  window.history.replaceState(null, "", "/");
});

describe("the view in the address (spec 038)", () => {
  it("writes every setting as a parameter of its own, readable in the address bar", () => {
    const params = viewToParams({ layout: "gv-neato", domains: ["a.Orders", "b.Billing"], disabled_kinds: ["core"], disabled_changes: [], one_hop: false, boundary: true, rankdir: "TB", paint: "kinds" });
    expect(params).toEqual({ layout: "gv-neato", domains: "a.Orders,b.Billing", off_kinds: "core", off_changes: "", one_hop: "0", boundary: "1", rankdir: "TB", paint: "kinds" });
  });

  it("reads back exactly what it wrote — an empty list too, which is not the same as no setting", () => {
    const settings = { domains: [], disabled_entities: ["x.Player"], disabled_changes: ["unchanged", "added"], one_hop: true, layout: "gv-dot-tb", paint: "kinds", paint_diff: "domains" };
    const view = paramsToView(new URLSearchParams(viewToParams(settings)));
    expect(view).toEqual({ settings });
    expect(paramsToView(new URLSearchParams("")).settings).toEqual({});
  });

  it("ignores a parameter out of shape rather than guess", () => {
    expect(paramsToView(new URLSearchParams("one_hop=yes&layout=")).settings).toEqual({});
  });

  it("is put into the address keeping every other parameter, and stays there through the next navigation", () => {
    window.history.replaceState(null, "", "/?view=domain-erd&domain=a.Orders");
    setUrlView({ off_kinds: "core", paint: "changes" });
    expect(new URLSearchParams(window.location.search).get("domain")).toBe("a.Orders");
    expect(new URLSearchParams(window.location.search).get("off_kinds")).toBe("core");
    syncUrlToState(null, { kind: "erd", qualifier: "a.Orders" });
    expect(new URLSearchParams(window.location.search).get("paint")).toBe("changes");
    setUrlView({});
    expect(new URLSearchParams(window.location.search).get("off_kinds")).toBeNull();
  });

  it("becomes the page's own settings when the page opens with it", () => {
    seedPageSettings("domain-erd|a.Orders", paramsToView(new URLSearchParams("off_kinds=core&one_hop=0")).settings);
    expect(shownPageSettings("domain-erd|a.Orders", null)).toEqual({ disabled_kinds: ["core"], one_hop: false });
  });

  it("follows the room's settings inside a room, not the tab's own", () => {
    seedPageSettings("p", { layout: "gv-neato" });
    expect(shownPageSettings("p", { settings: { p: { layout: "gv-circo" } }, set: () => undefined })).toEqual({ layout: "gv-circo" });
  });

  it("carries where the diagram is looked at — zoom and the diagram point at the centre — and reads it back", () => {
    const params = cameraToParams({ x: 1234.5678, y: -98.76, zoom: 0.4567 });
    expect(params).toEqual({ zoom: "0.457", at: "1234.6,-98.8" });
    expect(paramsToCamera(new URLSearchParams(params))).toEqual({ x: 1234.6, y: -98.8, zoom: 0.457 });
  });

  it("names no view when the address has none or one out of shape", () => {
    expect(cameraToParams(null)).toEqual({});
    expect(paramsToCamera(new URLSearchParams(""))).toBeNull();
    expect(paramsToCamera(new URLSearchParams("zoom=0&at=1,2"))).toBeNull();
    expect(paramsToCamera(new URLSearchParams("zoom=1&at=nowhere"))).toBeNull();
  });
});

