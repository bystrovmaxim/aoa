<!-- translated-from: iop-performative_draft.md @ 2026-06-22T13:05:56Z (filesystem mtime; draft is gitignored, no git history) · sha256:9ecdd5ac1269 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# The performative: why an IOP invariant creates intent rather than describing it

<table width="100%"><tr>
  <td align="left"><a href="philosophy.md">AOA Philosophy</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="../research/iop-foundations.md">IOP: atoms and molecules</a></td>
</tr></table>

---

In 1955 the philosopher John Austin made an observation that changed the theory of language. He noticed that not all utterances are alike in nature.

Some describe reality: "the door is open," "there are three items in the basket," "the user has the manager role." You can check them for truth. Austin called these **constatives**.

Other utterances create reality. "I declare this meeting open." "I swear to tell the truth." "Do you take this person to be your husband?" — "I do." The moment these words are spoken, nothing is being described — something is happening. Austin called these **performatives**. You can't check them for truth: they simply take effect, or they don't.

This distinction explains why Intent-Oriented Programming works the way it does.

## Traditional code — a constative

Description usually lives next to code: comments, documentation, architecture diagrams, contracts in a README. All of these are constatives. They describe an intent that already exists somewhere — in the author's head, in a requirement, in a workflow — and which the code supposedly implements.

A constative always has two sides: the utterance and the reality it talks about. Which means a gap between them is always possible. Today the comment is accurate; in six months it isn't. The documentation says one thing, the implementation does another, the test checks a third. This isn't a mistake by any particular team. It's a structural consequence of intent and code being two different objects — each with its own life, each with its own history of changes.

## The IOP invariant — a performative

`@check_roles(AdminRole)` doesn't state that AdminRole is required. It **establishes** that requirement at the moment it's declared. It doesn't describe a fact — it creates one.

That's a performative.

Wherever a constative lives, there are two places: the utterance and the reality. Wherever a performative lives, there is one. "I declare this meeting open" is not a description of a meeting that opened somewhere else. It *is* the moment of opening, itself.

The same goes for `@check_roles(AdminRole)` and the AdminRole requirement — they are one and the same thing. There is no separate "reality of the intent" that the decorator describes more or less accurately. The intent exists exactly to the extent that this decorator exists.

This is exactly why drift is impossible by construction. There's nothing to diverge: there aren't two objects, one of which could fall behind the other. There is one object, and it's the code.

## A performative without enforcement is not an invariant

A performative has one condition: it has to take effect. "I declare this meeting open," said in an empty room, with no agenda, with no one present — that's words, not an event. The form is there, but not the force.

A `@check_roles` decorator with no machine that reads it and applies it on every call is an annotation, not an invariant. A beautiful form with zero architectural weight.

Hence a principle that can't be sidestepped:

> **An unenforced rule is not an IOP invariant. It's a team convention.**

If a rule isn't checked by the machine, it's a constative wearing a performative's clothes. It might look like an invariant, but it works like documentation. Which means it goes stale over time.

## Three conditions under which a performative has force

A performative doesn't take effect at the moment it's written. It takes effect every time the system is assembled, starts up, or executes a call. For that to be true, three conditions are needed.

**Local explicitness.** The intent must exist within the same unit of code that carries it — not in a nearby comment, not in a team convention, not in external configuration. The operation itself must be able to point to it. If a fact about the operation can't be read from the operation itself, that's backstage knowledge, not an invariant.

**Continuous enforcement.** An invariant is not a snapshot taken during review. A violation must make assembly, startup, or execution impossible, regardless of when or by whom it was introduced. That's the difference between "we looked at this two years ago" and "the system won't start if this is no longer true."

**Accumulation into a whole.** A description of the system — a graph, documentation, an architecture map — must be computed from the same declarations. If it exists separately, it's just another constative. With one more possible gap.

This is exactly Intent Explicit, Intent Enforced, Intent Accumulative. Now it's clear where they come from: all three are requirements for a performative to have real force, rather than being a decorative form.

## Atoms, molecules, grammar

In AOA the performative nature of invariants shows up through a three-level hierarchy.

**Atoms** are minimal, checkable invariants: `@check_roles`, `@result_string`, `@depends`, `@compensate`, `@summary_aspect`, `@connection`. Each is one performative act answering one question. Who has the right? What is promised to the next step? Which port is allowed? How is the effect of a step rolled back?

**Molecules** are stable units of behavior assembled from atoms: `Action` and `Resource`. They have different natures, and that isn't a convention — it's an architectural fact. `Action` orchestrates a business scenario: roles, pipeline, state, recovery, result. `Resource` provides a controlled exit to the outside world: enumerable, with no business decisions inside. You can't mix them, not because it's forbidden, but because the system doesn't recognize such a construction as valid.

**Grammar** is the assembly rules that make invariants real. It defines not what's recommended, but what's admissible at all. You can't silently break it — that too is a property of a performative: violating a performative destroys the very fact it constituted.

## The boundary — where the performative takes effect

A traditional service method often combines everything inside: authorization, reading data, a business decision, writing, error handling. You have to reconstruct the meaning from the implementation.

In IOP, intent concentrates at an operation's boundaries: who may enter (`@check_roles`), what must arrive (`Params`), what must leave (`@result_*`), which effects are allowed (`@connection`), what to do on failure (`@compensate`, `@on_error`). This is exactly where the performative either takes effect — accepts the call, executes the step, fixes the promise — or is violated: the system fails right at the point of violation, not later as an undebuggable `KeyError`.

The boundary isn't a limitation of the architecture. The boundary is the primary carrier of meaning.

## IOP is a paradigm, not a language

This distinction matters.

An external intent-description language reproduces the same problem. There's an intent description — and there's code that implements it. Two artifacts. A possible gap. A need to synchronize. Drift.

IOP doesn't propose describing code from the outside. It proposes building code so that intent is a performative part of its structure. AOA is not a compiler for intent-descriptions into Python. It's a development paradigm, implemented in Python: a way of writing code in which intent is constituted in the very same act as the implementation.

The difference isn't syntactic. The difference is ontological.

## The absence of a possibility is also an architectural fact

The performative nature of invariants explains one more IOP principle that's easy to miss.

If the port you need isn't in the `Resource`, the role you need isn't in the system, the aspect you need isn't in the operation — that's not a developer's oversight. It's an architectural fact: that possibility doesn't exist in this system.

IOP defines not just how to build. It defines how to stop correctly. A system that can clearly fix "this possibility doesn't exist" and doesn't invite improvising around the absence is a system with no backstage — not only because what exists is described explicitly, but also because what doesn't exist doesn't pretend to.

---

<table width="100%"><tr>
  <td align="left"><a href="philosophy.md">AOA Philosophy</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="../research/iop-foundations.md">IOP: atoms and molecules</a></td>
</tr></table>
