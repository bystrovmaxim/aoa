// src/components/history/VersionPicker/TrackLegend.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { PROPOSAL_LOOK } from "@/components/history/VersionTrack/proposalLook";
import { TrackLegend } from "./TrackLegend";

afterEach(cleanup);

describe("the track's legend", () => {
  it("names every kind of point, in the order they stand, and the other marks", async () => {
    render(<TrackLegend />);
    fireEvent.mouseOver(screen.getByRole("button", { name: "Reading the track" }));
    const terms = ["Direct push", "Merged", ...Object.values(PROPOSAL_LOOK).map((look) => look.name), "Live", "Size", "Flag", "The chosen point"];
    for (const term of terms) expect(await screen.findByText(term)).toBeTruthy();
  });

  it("tells the keys beside the marks", async () => {
    render(<TrackLegend />);
    fireEvent.mouseOver(screen.getByRole("button", { name: "Reading the track" }));
    expect(await screen.findByText(/One version older or newer/)).toBeTruthy();
    expect(screen.getByText(/The previous or the next change/)).toBeTruthy();
    expect(screen.getByText("Take it to an end of the track")).toBeTruthy();
  });

  it("shows no draft: a draft pull request is not on the track", async () => {
    render(<TrackLegend />);
    fireEvent.mouseOver(screen.getByRole("button", { name: "Reading the track" }));
    await screen.findByText("Merged");
    expect(screen.queryByText("Draft")).toBeNull();
  });
});
