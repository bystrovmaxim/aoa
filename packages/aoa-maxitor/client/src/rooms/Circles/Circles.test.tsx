// src/rooms/Circles/Circles.test.tsx
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Circles, ringedBox } from "@/rooms/Circles";
import { FollowFrame } from "@/rooms/FollowFrame";
import { setParticipantCardOpen } from "@/rooms/participantCardOpen";
import type { Participant } from "@/rooms/protocol";

const person = (id: string, colour: string): Participant => ({ id, name: id, colour, page: "view=domain-erd", visible: true, away: false });
const people = [person("Anna", "#2563eb"), person("Boris", "#dc2626"), person("Vera", "#15803d")];

function circles() {
  return render(
    <Circles
      participants={people}
      youId="Anna"
      yourPage="view=domain-erd"
      pageLabel={() => "ERD"}
      followers={() => 1}
      onRename={vi.fn()}
      onGoTo={vi.fn()}
      follows={{ Anna: null, Boris: null, Vera: null }}
      onFollow={vi.fn()}
      onStopFollowing={vi.fn()}
      compact={false}
    />,
  );
}

afterEach(() => {
  cleanup();
  setParticipantCardOpen(false);
});

describe("the room bar's circles (spec 029, FR-050, FR-051)", () => {
  it("are 22 px in a 29 px box that holds the ring", () => {
    circles();
    expect(ringedBox(22)).toBe(29);
    for (const name of ["Anna", "Boris", "Vera"]) {
      const button = screen.getByRole("button", { name: new RegExp(`^${name}`) });
      expect(getComputedStyle(button).width).toBe("29px");
      expect(getComputedStyle(button).height).toBe("29px");
      const circle = [...button.querySelectorAll("span")].find((s) => getComputedStyle(s).width === "22px");
      expect(circle).toBeDefined();
    }
  });

  it("draw your ring inside the box and the focus ring inside it too", () => {
    circles();
    const yours = screen.getByRole("button", { name: /^Anna \(you\)/ });
    const ringBox = [...yours.querySelectorAll("span")].find((s) => getComputedStyle(s).width === "29px")!;
    expect(getComputedStyle(ringBox).boxShadow).toMatch(/^inset /);
    expect(document.head.innerHTML).toMatch(/outline-offset:\s*-2px/);
    expect(document.head.innerHTML).not.toMatch(/outline-offset:\s*3px/);
  });

  it("keep the follower count inside the box sideways", () => {
    circles();
    const badge = screen.getByLabelText("1 following you");
    expect(getComputedStyle(badge).right).toBe("0px");
  });
});

describe("the follow pill while a card is open (spec 029, FR-052)", () => {
  it("steps aside, and comes back when the card closes", () => {
    render(<FollowFrame following={people[1]!} onStop={vi.fn()} />);
    const pill = screen.getByRole("status");
    expect(getComputedStyle(pill).visibility).toBe("visible");
    act(() => setParticipantCardOpen(true));
    expect(getComputedStyle(pill).visibility).toBe("hidden");
    act(() => setParticipantCardOpen(false));
    expect(getComputedStyle(pill).visibility).toBe("visible");
  });
});
