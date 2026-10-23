# Contract: a dictionary member is checked after user validation

**Feature**: `specs/017-explicit-entity-relations` | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Research**: [../research.md](../research.md)

A dictionary member is shared data: every consumer reads the same instance through `by_code()`. This contract fixes what a member's property may be, when the answer is produced, what is refused, and what is never done to a value that disagrees.

## 1. Supported property types

| Accepted | Refused |
| --- | --- |
| `str`, `int`, `float`, `bool` | `list`, `dict`, `set`, `frozenset` |
| `Decimal`, `date`, `datetime`, `time`, `UUID` | a nested Pydantic model |
| `Literal[...]`, `Optional[X]` of an accepted type | `Any`, or an unsupported container inside an accepted one |
| `tuple[...]` of accepted types, recursively | a tuple holding a `list` |
| an `Enum` subclass, whose value is itself accepted | an `Enum` whose value is a `list`, `dict`, `set` or model |

## 2. The runtime check

| Rule | Statement |
| --- | --- |
| When | after the member is constructed by the declaration machinery and before `members`, `codes()` and `by_code()` publish it |
| What | the runtime value must agree with the declared annotation **and** satisfy the type set recursively |
| Why both | the baseline accepts a value that is immutable but of another type and exports a shape its schema does not describe |
| `Enum` | the member's own value is checked by the same set; the annotation alone proves nothing |
| Nesting | tuples and `Optional` unwrap recursively; a mapping or list inside any of them is refused at its position |
| Scope | dictionary members only; a state type keeps its present freedom |

## 3. What is refused, and what is never done

| Situation | Answer |
| --- | --- |
| after-validator returns `list(labels)` for `tuple[str, ...]` | refused: dictionary, member, property path and `list` |
| after-validator returns `",".join(labels)` (a `str`) | refused: names the declared `tuple[str, ...]` and the actual `str` |
| `Enum` member's value is `["a", "b"]` | refused at the enum property's path |
| a tuple holds a dictionary | refused at the nested path |
| a valid validator returns an equal tuple | accepted and published |
| the framework would freeze a list into a tuple | not the contract — the declaration is refused instead |
| the value would be coerced or re-annotated | not done: the declared type is the declaration author's |

## 4. Publication and export

| Rule | Statement |
| --- | --- |
| Publication | a refused member never reaches `members`, `codes()` or `by_code()` |
| Identity | the published member is still the one declared attribute, in declaration order |
| Export | `to_reference()` is unchanged: the JSON export of the value |
| Independence | editing an exported array never changes the declared tuple or a later export |
| Schema | the serialization schema of a dictionary describes these members, and every definition it references resolves |

## 5. The refusal message

One message per member, naming four things in this order: the dictionary, the member's code or attribute, the property path, and the actual type. Example:

```text
LabelsEnumEntity: the property 'labels' of member ITEM holds list
(expected tuple[str, ...]); a declared value cannot keep a mutable value.
```

The message is English, as every refusal in this repository is, and the supported set is named in the documentation rather than repeated in every message.
