// src/rooms/followCircle.test.ts
import { describe, expect, it } from "vitest";
import { followsYou, wouldCloseCircle } from "@/rooms/followCircle";

// The same cases as the server's tests/test_rooms_follow_circle.py: the client disables what the server refuses.
describe("the follow circle", () => {
  it("lets anyone follow when nobody follows anyone", () => {
    expect(wouldCloseCircle({}, "boris", "anna")).toBe(false);
  });

  it("refuses a direct circle", () => {
    expect(wouldCloseCircle({ anna: "boris" }, "boris", "anna")).toBe(true);
  });

  it("refuses an indirect circle both ways", () => {
    const follows = { anna: "boris", vera: "anna" };
    expect(wouldCloseCircle(follows, "boris", "anna")).toBe(true);
    expect(wouldCloseCircle(follows, "boris", "vera")).toBe(true);
  });

  it("counts following oneself as a circle", () => {
    expect(wouldCloseCircle({}, "anna", "anna")).toBe(true);
  });

  it("allows a chain without the follower", () => {
    expect(wouldCloseCircle({ vera: "anna" }, "boris", "vera")).toBe(false);
  });

  it("ends on links that already loop", () => {
    expect(wouldCloseCircle({ x: "y", y: "x" }, "boris", "x")).toBe(false);
  });
});

describe("who follows you", () => {
  it("tells a direct follower from one through others", () => {
    const follows = { anna: "boris", vera: "anna", gleb: null };
    expect(followsYou(follows, "boris", "anna")).toBe("direct");
    expect(followsYou(follows, "boris", "vera")).toBe("anna");
    expect(followsYou(follows, "boris", "gleb")).toBeNull();
    expect(followsYou(follows, "anna", "boris")).toBeNull();
  });
});
