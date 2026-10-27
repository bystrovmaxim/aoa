// src/lib/useCaseRoleLabels.test.ts
import { afterEach, describe, expect, it } from "vitest";
import { buildDomainUseCaseDotBundle } from "@/lib/buildDomainUseCaseDotSource";
import { bindRoleLabels, ROLE_HOVER_CLASS, roleLabelSx } from "@/lib/useCaseRoleLabels";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("role labels on the use-case diagram (spec 029, FR-042)", () => {
  it("marks every role node in the DOT source", () => {
    const { dot } = buildDomainUseCaseDotBundle(
      {
        domain: { id: "sales", label: "Sales", short_label: "Sales", accent_color: "#2563eb" },
        actions: [{ id: "pay", label: "Pay", short_label: "Pay", domain_id: "sales", domain_short_label: "Sales", accent_color: "#2563eb", role_ids: ["manager"] }],
        roles: [{ id: "manager", label: "Manager", short_label: "Manager" }],
        edges: [{ edge_kind: "association", source_id: "manager", target_id: "pay" }],
      },
      "LR",
      { roleActorImageUrl: "" },
      { boundary: true },
    );
    expect(dot).toMatch(/r_manager \[class="uc-role" /);
  });

  it("are hidden until the role is hovered — by a mouse or by a follower's replayed hover", () => {
    // As Graphviz writes it: the hyphen escaped in the class attribute.
    document.body.innerHTML = `<div id="panner"><svg><g id="node1" class="node uc&#45;role"><text>Manager</text></g><g id="node2" class="node"><text>Pay</text></g></svg></div>`;
    const panner = document.getElementById("panner")!;
    const controller = new AbortController();
    bindRoleLabels(panner, controller.signal);
    const role = panner.querySelector("#node1")!;
    expect(role.classList.contains(ROLE_HOVER_CLASS)).toBe(false);
    role.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false }));
    expect(role.classList.contains(ROLE_HOVER_CLASS)).toBe(true);
    role.dispatchEvent(new MouseEvent("mouseleave", { bubbles: false }));
    expect(role.classList.contains(ROLE_HOVER_CLASS)).toBe(false);
    // An action is not a role: its label always shows.
    panner.querySelector("#node2")!.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false }));
    expect(panner.querySelector("#node2")!.classList.contains(ROLE_HOVER_CLASS)).toBe(false);
    controller.abort();
  });

  it("hide only a role's text, and show it on a hovered role", () => {
    expect(roleLabelSx).toEqual({
      "& g.node.uc-role text": { visibility: "hidden" },
      "& g.node.uc-role.is-hovered text": { visibility: "visible" },
    });
  });
});
