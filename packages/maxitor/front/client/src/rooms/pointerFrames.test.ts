// src/rooms/pointerFrames.test.ts
import { afterEach, describe, expect, it } from "vitest";
import { clientInFrame, inFrame } from "@/rooms/pointerFrames";

afterEach(() => {
  document.body.innerHTML = "";
});

/** A panel named ``frame`` at ``left``, ``top`` on the screen, scrolled ``scrollLeft`` across. */
function panel(frame: string, left: number, top: number, scrollLeft = 0): HTMLDivElement {
  const element = document.createElement("div");
  element.setAttribute("data-pointer-frame", frame);
  element.getBoundingClientRect = () => new DOMRect(left, top, 300, 200);
  Object.defineProperty(element, "scrollLeft", { value: scrollLeft });
  element.innerHTML = "<span>a control</span>";
  document.body.appendChild(element);
  return element;
}

describe("a pointer over a panel that names its frame (spec 038)", () => {
  it("is sent as its place in the panel's content, scroll included", () => {
    const track = panel("version-track", 500, 100, 40);
    expect(inFrame(track.querySelector("span"), { x: 520, y: 110 })).toEqual({ x: 60, y: 10, frame: "version-track" });
  });

  it("stands in the window of a panel whose scroll a follower shares, so it stays when the rows move under it", () => {
    const list = panel("changes", 500, 100, 40);
    list.setAttribute("data-pointer-shared-scroll", "");
    const sent = inFrame(list.querySelector("span"), { x: 520, y: 110 });
    expect(sent).toEqual({ x: 20, y: 10, frame: "changes" });
    expect(clientInFrame("changes", sent!)).toEqual({ x: 520, y: 110 });
  });

  it("lands on the same place of the follower's panel, wherever it opened and however far it scrolled", () => {
    panel("version-track", 200, 300, 0);
    expect(clientInFrame("version-track", { x: 60, y: 10 })).toEqual({ x: 260, y: 310 });
  });

  it("is not a framed position outside every frame, and not drawn where no panel of that name is", () => {
    const outside = document.createElement("span");
    document.body.appendChild(outside);
    expect(inFrame(outside, { x: 1, y: 1 })).toBeNull();
    expect(clientInFrame("versions", { x: 1, y: 1 })).toBeNull();
  });
});
