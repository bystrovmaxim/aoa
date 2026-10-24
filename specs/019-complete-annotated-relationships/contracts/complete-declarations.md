# Contract: Complete Entity Relationship Declarations

**Source**: [Specification](../spec.md), FR-001–010, FR-015–019.

## Universal rule

Core, Assoc, Detail, Spec and Enum entity-valued fields require a supported container inside Annotated, exactly one Inverse or NoInverse marker and one assignment-side Field with nonblank description. Check every permitted owner/target combination independently. Assoc endpoints and graph-hidden/excluded hosts have no exemption. Bare/nullable bare types, raw collections, bare Annotated targets and NoRelation do not satisfy the rule. State retains its separate Lifecycle contract; ordinary scalars remain ordinary fields.

Use existing names CompositeOne/CompositeMany. No new relationship-kind aliases are introduced. Dictionary target restrictions are specified in [dictionary-association.md](dictionary-association.md).

## Direction and cross-module resolution

- `Inverse(Target, "field")`: Target must be the resolved container target by identity.
- `Inverse(field_name="field")`: derive Target from the resolved container; support ordinary relations as well as specialization heads.
- `NoInverse()`: an intentionally one-way relationship, not a missing-marker fallback.
- Each paired endpoint requires reciprocal Inverse markers. Inverse may not target a NoInverse field.
- Resolve forward annotations in the model's explicit composition-root namespace before checking them; do not require declaration modules to import each other at runtime.
- An unresolved/missing/mismatched reverse field blocks publication. Do not repeat get_type_hints against unprepared module globals after a successful explicit model_rebuild.

Existing compatibility/classifier checks remain. There is no new Composite/Aggregate/Association pair matrix.

### Inherited and overridden inverse endpoints

Distinguish the **effective host**, whose completed fields are being validated/projected, from the **declaring owner**, which introduced the effective relationship declaration. An unchanged inherited field keeps the declaring owner's endpoint identity. This does not skip completeness checks on the effective host.

Resolve reciprocal relationships by canonical endpoint identity, `(declaring_owner_class_identity, field_name)`. Looking up a field on a target class first resolves its effective declaration and declaring owner. The reverse marker must resolve back to the same canonical originating endpoint. An explicit class in Inverse still must be the identical resolved container target; do not replace this check with a blanket issubclass allowance.

- If Base.items and Item.owner are a valid reciprocal pair, and Child inherits Base.items unchanged, Child's inherited field remains the Base.items endpoint for reciprocity. Item.owner may continue to target Base; Child does not need a duplicate reverse field.
- Any explicit field override creates a new endpoint owned by the overriding class, even if it repeats the same relationship syntax. It must independently satisfy completeness and reciprocity. A generic substitution that changes the resolved relationship target/signature is a semantic override and must also be checked as a new effective endpoint.
- If Child overrides items but its claimed reverse still resolves only to Base.items, refuse Child's declaration. The author must supply a reciprocal pair for the new endpoint, or explicitly declare a genuinely one-way relationship with NoInverse. The base pair is not silently retargeted.
- In multiple/diamond inheritance, use the effective field selected by normal model/MRO resolution; unchanged inherited copies of the same declaration share one canonical endpoint. Repeated inheritance must not create duplicate validation endpoints. Distinct same-named declarations are not interchangeable.
- Existing specialization alternatives retain their dedicated classifier/target restrictions. Canonicalization does not make an otherwise invalid specialization subclass or vocabulary legal.

Graph projection remains per effective host and field: a graph-visible Child inherits its own field/edge projection with Child as source. Canonicalization deduplicates validation identity, not graph entities or edges belonging to different hosts. Retain the concrete resolved target from each annotation; never auto-retarget a base relationship to a child.

| Case | Result |
| --- | --- |
| Valid Base/Item pair and unchanged inherited Child.items | Pass completeness and reciprocal checks; preserve Base/Item declarations |
| Child overrides items and provides a reciprocal endpoint for Child.items | Pass, subject to existing compatibility/classifier rules |
| Child overrides items but the claimed reverse still names only Base.items | Refuse the new Child endpoint |
| Grandchild inherits a valid Child override unchanged | Reuse Child's endpoint identity; project Grandchild separately |
| Base pair is incomplete/nonreciprocal or claims a NoInverse reverse | Refuse; inheritance supplies no exemption |
| Diamond inherits the same unchanged declaring endpoint twice | Validate one canonical endpoint and project one field per effective host |
| Same names on unrelated declaring classes | Do not pair by names or subclass guessing |

## Nullable/default behavior

Keep the relation container inside Annotated even for nullable fields. Existing relation defaults are unchanged: no default_factory and no concrete relation default; explicit None is allowed only on a nullable field. Missing values remain required unless an allowed default is written.

## Source spelling versus normalized runtime metadata

Pydantic merges field declarations. Runtime validation must inspect completed annotation and metadata and refuse incomplete/conflicting semantics without requiring source availability. The separate explicit-root source check enforces the specified placement/count of Field in maintained source/examples. It must not claim FieldInfo can recover lost source spelling.

## Failure contract

Use the existing EntityFieldDeclarationError family for declaration/reciprocity failures, retaining the owner and field. Distinguish incomplete shape, missing/conflicting markers, unresolved target, missing/nonreciprocal reverse field, explicit target mismatch, dictionary target restriction and existing compatibility refusal. Each message supplies a complete supported replacement; never recommend bare Enum or NoRelation.

Exact message strings are fixed with implementation regression tests and captured outputs, not invented as planning evidence. Existing earlier class-construction errors stay documented at their actual boundary.

## Entry points and isolation

Coordinator build and its factory/machine paths must refuse invalid declarations before successful publication. A supported direct EntityGraphNode projection must not silently bypass completeness/relevant inverse checks. An injected coordinator must already represent a successful validated build; verify the existing supported injection contract before changing consumers.

Negative model declarations must be isolated from global loaded-class builds. Exclusion cannot be used to shelter invalid fixture declarations after this change.
