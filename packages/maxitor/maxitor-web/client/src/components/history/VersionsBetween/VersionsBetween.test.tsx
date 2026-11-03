// src/components/history/VersionsBetween/VersionsBetween.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { versionsBetween, VersionsBetween } from "./VersionsBetween";

afterEach(cleanup);

/** Five versions, ``#1`` the oldest, each with a two-line message. */
const versions: HistoryVersion[] = [1, 2, 3, 4, 5].map((n) => ({
  sha: `${n}`.padEnd(40, "a"),
  date: "2026-10-01T00:00:00Z",
  message: `Change ${n}\n\nWhy change ${n} was made.`,
  tags: [],
  nodes: 1,
  edges: 1,
  source: `s${n}`,
}));
const key = (n: number) => versions[n - 1].sha.slice(0, 12);

describe("the versions between A and B", () => {
  it("are the points strictly between them, newest first", () => {
    expect(versionsBetween(versions, null, null, [], { a: key(1), b: key(5) }).map((each) => each.message?.split("\n")[0])).toEqual(["Change 4", "Change 3", "Change 2"]);
  });

  it("run up to Live, leaving out the newest version while Live runs exactly its graph", () => {
    expect(versionsBetween(versions, "https://live", null, [], { a: key(3), b: "live" })).toHaveLength(2);
    expect(versionsBetween(versions, "https://live", versions[4].sha, [], { a: key(3), b: "live" })).toHaveLength(1);
  });

  it("leave out open pull requests: they are not on the way from A to Live", () => {
    const proposal: HistoryVersion = { ...versions[0], sha: "9".padEnd(40, "b"), pr: { number: 9, title: "Open", body: "", url: "u" } };
    expect(versionsBetween(versions, "https://live", null, [proposal], { a: key(4), b: "live" }).map((each) => each.sha)).toEqual([versions[4].sha]);
  });

  it("open newest first, each closed row its name and its message's first line", () => {
    render(<VersionsBetween versions={versions} live={null} range={{ a: key(1), b: key(4) }} repository={null} />);
    fireEvent.click(screen.getByRole("button", { name: /2 versions between/ }));
    const rows = screen.getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual(["#3Change 3", "#2Change 2"]);
    expect(screen.queryByText(/Why change/)).toBeNull();
  });

  it("open a row's whole message on a click", () => {
    render(<VersionsBetween versions={versions} live={null} range={{ a: key(1), b: key(3) }} repository={null} />);
    fireEvent.click(screen.getByRole("button", { name: /1 version between/ }));
    fireEvent.click(screen.getByRole("button", { name: /Change 2/ }));
    expect(screen.getByTestId("message").textContent).toBe("Change 2\n\nWhy change 2 was made.");
  });

  it("are absent when A and B are neighbours", () => {
    const { container } = render(<VersionsBetween versions={versions} live={null} range={{ a: key(2), b: key(3) }} repository={null} />);
    expect(container.textContent).toBe("");
  });
});
