// src/rooms/InviteCard/InviteCard.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KEY_DOTS } from "@/lib/historyAddress";
import { InviteCard } from "./InviteCard";

const LINK = "https://maxitor.example/?history=h&b=abc&room=r#key=the-secret-key";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("the invite card of a room on a private history", () => {
  it("shows the link with its key as dots and copies the real one", async () => {
    const written: string[] = [];
    vi.stubGlobal("navigator", { ...navigator, share: undefined, clipboard: { writeText: async (text: string) => void written.push(text) } });
    render(<InviteCard anchor={document.body} link={LINK} copyOnOpen={false} onClose={() => undefined} />);
    const field = screen.getByLabelText("Room link") as HTMLInputElement;
    expect(field.value).toBe(`https://maxitor.example/?history=h&b=abc&room=r#key=${KEY_DOTS}`);
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));
    await vi.waitFor(() => expect(written).toEqual([LINK]));
  });
});
