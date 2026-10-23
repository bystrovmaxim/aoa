# Contract: a field whose type is a dictionary is a declared reference

**Feature**: `specs/018-dictionary-reference` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

A model author writes one line. This contract fixes what that line may say when its type is a closed dictionary, what the framework answers when it says something else, and where the answer is produced.

## 1. The accepted forms

```python
# the reference — the dictionary type itself, as #241 decided
currency: CurrencyEnumEntity = Field(description="Money unit")

# the nullable reference
settlement_currency: CurrencyEnumEntity | None = Field(default=None, description="Optional unit")
```

| Rule | Statement |
| --- | --- |
| Form 1 | `D` — a `BaseEnumEntity` descendant |
| Form 2 | `D \| None` |
| Content | either form holds a declared value of that dictionary, or its reference object |
| Default | unchanged by this contract; a reference does not acquire the relation-field default rules |
| Nullability | `\| None` is the annotation's choice, exactly as for any field |

## 2. What is refused

| Written | Answer |
| --- | --- |
| `items: tuple[D, ...]`, `list[D]`, `Sequence[D]`, `set[D]`, `frozenset[D]`, `dict[K, D]` | refused: a collection of dictionary values has no declared form; the message names `D` and `D \| None` |
| `currency: AssociationOne[D]` and the other seven containers | refused: a dictionary value is a shared reference, not an association target |
| `Annotated[D, NoRelation("…")]` | refused: the bare dictionary type already declares the reference |
| `currency: EmptyEnumEntity` | refused: the dictionary declares no values |
| `currency: ExcludedEnumEntity` | refused: the dictionary is not a node of the graph, so the reference cannot be drawn |

Each refusal names the owner, the field and the resolved type, and shows the form that fits. Every message is one paragraph: what is wrong with this field, and what to write instead.

A dictionary that is both empty and outside the graph is reported as empty first: `@entity`
already refuses an empty dictionary at class creation, so the catalogue is the cause the author
can fix, and the graph-model refusal is the second answer, not the first.

```text
OfferCoreEntity.regions: a collection of dictionary values has no declared form
(tuple[RegionEnumEntity, ...]). A dictionary reference is one value: write
region: RegionEnumEntity, or region: RegionEnumEntity | None for an optional one.
```

## 3. What is accepted unchanged

| Field | Why |
| --- | --- |
| `id: str`, `amount: float`, `note: str \| None` | an ordinary scalar |
| `lifecycle: OrderLifecycle` | a lifecycle reference |
| `params: SomeParams` | a schema type, outside the ERD and outside this rule |
| `showcase: Annotated[AssociationOne[ShowcaseCoreEntity], Inverse(...)]` | a structural relation, judged by #249 and untouched here |

## 4. Where and when the rule runs

| Rule | Statement |
| --- | --- |
| Boundary | the declaration pass in `NodeGraphCoordinator.build()`, before the graph's referential-integrity pass |
| Input | the resolved annotation from `model_fields` |
| Forward references | judged after resolution; a name that never resolves keeps its existing failure and is not reported as a scalar |
| Classes outside the graph | a class marked `exclude_graph_model` is not judged |
| Evaluating strings | never — no `eval`, no `get_type_hints` re-run, no inference from a field's name |
| Inherited fields | judged on the class that reports them in `model_fields` |
| One file | the same validator that judges a structural entity; the dictionary is another kind in one classifier |

## 5. The empty catalogue and the excluded dictionary

| Rule | Statement |
| --- | --- |
| Empty catalogue | refused by the rule, in every shape, naming the field and the dictionary |
| Not a graph model | refused by the rule, naming the field and the dictionary |
| Why | an empty dictionary could never fill the field, and a dictionary without a node would leave the reference edge dangling |
| Where the check lives | the validator only; the graph edge's own check is deleted |
