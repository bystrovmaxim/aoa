# Diagnosing a specialization declaration

Use this guide when a model that declares variant-specific details is refused, or when you need to check exactly what a declaration rule means. The examples use a record catalogue: `VinylRecordEntity` holds common information, and three pressing classes hold different kinds of details. The common class is the **head** and the pressing classes are its **alternatives**. If these terms are new, first read the [relations tutorial](../tutorials/step-21-relations.md#generalization-and-specialization).

Each experiment changes one aspect of a working declaration. Its script and notebook contain the complete model, the diagnostic call and the printed answer. The repairs below have also been checked through both the declaration validator and actual machine creation. Run the programs separately: AOA discovers loaded entity declarations, so importing an intentionally broken example into another experiment would change what that experiment validates.

## Start with a model that works

The common record contains `media`, a string naming the kind of pressing, and `pressing`, the reference to its details. `Classifier` associates the ordinary code field with the possible codes. Each pressing class points back through `record` and declares its own code. This is the unchanged preparation for the one-axis experiments below:


```python
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Classifier, Generalization, Inverse, Rel, Specialization
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class MusicDomain(BaseDomain):
    """Group the music catalogue declarations."""

    name = "music"
    description = "A music catalogue"


@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")


@entity(description="First pressing", domain=MusicDomain)
class FirstPressEntity(BaseEntity):
    """Describe the stamper used for a first pressing."""

    id: str = Field(description="Pressing identifier")
    stamper: str = Field(description="Stamper code")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Re-pressing", domain=MusicDomain)
class RepressEntity(BaseEntity):
    """Describe when an album was pressed again."""

    id: str = Field(description="Pressing identifier")
    year: int = Field(description="Re-pressing year")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["repress"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


@entity(description="Test pressing", domain=MusicDomain)
class TestPressEntity(BaseEntity):
    """Describe who approved a test pressing."""

    id: str = Field(description="Pressing identifier")
    approved_by: str = Field(description="Reviewer name")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["test"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")


for model in (VinylRecordEntity, FirstPressEntity, RepressEntity, TestPressEntity):
    model.model_rebuild()
```

Append this success check to that preparation:


```python
from aoa.action_machine.graph.validators.entity_specialization_validator import validate_entity_specializations

validate_entity_specializations()
ActionProductMachine(loggers=[])
print("Corrected model built")
```

Output:


```text
Corrected model built
```

`validate_entity_specializations()` is the declaration validator used during model building. Calling it directly is useful for diagnosis: it checks the loaded model without first constructing graph edges. This is a targeted diagnostic entry point, not something ordinary application startup needs to duplicate. Machine creation still performs the build.

For a broken experiment, replace the success check with the following diagnostic block. It catches only the expected declaration-error class; another exception or an unexpectedly accepted model is not disguised as a successful test.


```python
from aoa.action_machine.domain.exceptions import SpecializationDeclarationError
from aoa.action_machine.graph.validators.entity_specialization_validator import validate_entity_specializations

try:
    validate_entity_specializations()
except SpecializationDeclarationError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The broken declaration was accepted")
```

A declaration error names the specialization field, the head class and the condition that failed. For example, a missing code on an alternative is not a complaint about data read from storage: it points to a mismatch between class declarations. Several conditions can fail together; the first reported condition is not necessarily the only problem.

## Find the relevant experiment

- [The head has no classifier marker](#the-head-has-no-classifier-marker).
- [An alternative has no code](#an-alternative-has-no-code).
- [An alternative declares two codes](#an-alternative-declares-two-codes).
- [A head code has no matching alternative](#a-head-code-has-no-matching-alternative).
- [An alternative code is absent from the head](#an-alternative-code-is-absent-from-the-head).
- [Two alternatives claim one code](#two-alternatives-claim-one-code).
- [A code does not fit the field type](#a-code-does-not-fit-the-field-type).
- [The classifier names no field](#the-classifier-names-no-field).
- [The classifier names the relation itself](#the-classifier-names-the-relation-itself).
- [The reverse field name disagrees](#the-reverse-field-name-disagrees).
- [An alternative has no reverse declaration](#an-alternative-has-no-reverse-declaration).
- [An alternative has two reverse fields](#an-alternative-has-two-reverse-fields).
- [An alternative is not declared as an entity](#an-alternative-is-not-declared-as-an-entity).
- [Two axes use the same classifier](#two-axes-use-the-same-classifier).
- [Two heads claim the same alternative](#two-heads-claim-the-same-alternative).
- [A reverse declaration is outside the union](#a-reverse-declaration-is-outside-the-union).
- [A relation is used as classifier](#a-relation-is-used-as-classifier).
- [Two entities form a specialization cycle](#two-entities-form-a-specialization-cycle).
- [A second axis has a different alternative set](#a-second-axis-has-a-different-alternative-set).
- [Machine creation reports KeyError](#machine-creation-reports-keyerror).
- [Marker arguments fail before a build](#marker-arguments-fail-before-a-build).

## The head has no classifier marker

In the preparation, replace this declaration text:

```python
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
```

with nothing: remove just that marker or field declaration. Leave the other declarations unchanged.

[Script](../../examples/step_21_relations/20_error_missing_classifier.py) · [Notebook](../../examples/step_21_relations/20_error_missing_classifier.ipynb)


```bash
uv run python examples/step_21_relations/20_error_missing_classifier.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: is a specialization container but declares no Classifier marker; name the choosing field and the codes beside it
```

Without the marker, pressing names possible classes but does not name the code field. The specialization parser cannot describe the choice.

**Repair.** Restore the removed Classifier line on VinylRecordEntity.pressing. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## An alternative has no code

In the preparation, replace this declaration text:

```python
        Classifier("record", Literal["first"]),
```

with nothing: remove just that marker or field declaration. Leave the other declarations unchanged.

[Script](../../examples/step_21_relations/21_error_missing_code.py) · [Notebook](../../examples/step_21_relations/21_error_missing_code.ipynb)


```bash
uv run python examples/step_21_relations/21_error_missing_code.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: alternative 'FirstPressEntity' declares no code on 'record' — name it with Classifier(..., Literal[...])
```

FirstPressEntity still points back to VinylRecordEntity, but nothing associates it with the code first.

**Repair.** Restore Classifier("record", Literal["first"]) on FirstPressEntity.record. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## An alternative declares two codes

In the preparation, replace this declaration text:

```python
Classifier("record", Literal["first"])
```

with:

```python
Classifier("record", Literal["first", "early"])
```

[Script](../../examples/step_21_relations/22_error_multiple_codes.py) · [Notebook](../../examples/step_21_relations/22_error_multiple_codes.ipynb)


```bash
uv run python examples/step_21_relations/22_error_multiple_codes.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: alternative 'FirstPressEntity' must declare exactly one code on its reverse field, got ['first', 'early']
```

A single alternative must declare one code on its reverse field. The parser refuses the two-code declaration before building a mapping.

**Repair.** Keep only first on FirstPressEntity.record. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## A head code has no matching alternative

In the preparation, replace this declaration text:

```python
codes=Literal["first", "repress", "test"]
```

with:

```python
codes=Literal["early", "repress", "test"]
```

[Script](../../examples/step_21_relations/23_error_unknown_head_code.py) · [Notebook](../../examples/step_21_relations/23_error_unknown_head_code.ipynb)


```bash
uv run python examples/step_21_relations/23_error_unknown_head_code.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: code(s) ['early'] are named by the head but no alternative declares them
```

The head names early, while FirstPressEntity declares first. The two sets disagree.

**Repair.** Change early back to first on the head, or intentionally rename the code on both sides. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## An alternative code is absent from the head

In the preparation, replace this declaration text:

```python
codes=Literal["first", "repress", "test"]
```

with:

```python
codes=Literal["first", "repress"]
```

[Script](../../examples/step_21_relations/24_error_extra_alternative_code.py) · [Notebook](../../examples/step_21_relations/24_error_extra_alternative_code.ipynb)


```bash
uv run python examples/step_21_relations/24_error_extra_alternative_code.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: alternative(s) declare code(s) the head does not name: {'test': 'TestPressEntity'}
```

Every head code has an owner, but TestPressEntity declares test, which the head omitted. This is a real declaration that reaches the extra-code diagnostic.

**Repair.** Restore test in the head code list. Do not remove the class unless the model truly no longer permits that alternative. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## Two alternatives claim one code

In the preparation, replace this declaration text:

```python
Classifier("record", Literal["test"])
```

with:

```python
Classifier("record", Literal["first"])
```

[Script](../../examples/step_21_relations/25_error_duplicate_code.py) · [Notebook](../../examples/step_21_relations/25_error_duplicate_code.ipynb)


```bash
uv run python examples/step_21_relations/25_error_duplicate_code.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: code(s) ['test'] are named by the head but no alternative declares them
```

Two classes now claim first. The unchanged head also names test, which has lost its owner, so that missing-code diagnostic appears first.

**Repair.** Restore test on TestPressEntity.record. Check one unique code per alternative rather than relying on a particular duplicate-code message. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## A code does not fit the field type

In the preparation, replace this declaration text:

```python
media: str =
```

with:

```python
media: int =
```

[Script](../../examples/step_21_relations/26_error_classifier_type.py) · [Notebook](../../examples/step_21_relations/26_error_classifier_type.ipynb)


```bash
uv run python examples/step_21_relations/26_error_classifier_type.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: code 'first' cannot be stored by classifier field 'media' of type <class 'int'>
```

The declared word first cannot be validated as an integer. The check concerns the classifier annotation, not data fetched from a database.

**Repair.** Restore media: str; choose the field type appropriate to the data codes. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## The classifier names no field

In the preparation, replace this declaration text:

```python
Classifier(field="media",
```

with:

```python
Classifier(field="format",
```

[Script](../../examples/step_21_relations/27_error_classifier_missing_field.py) · [Notebook](../../examples/step_21_relations/27_error_classifier_missing_field.ipynb)


```bash
uv run python examples/step_21_relations/27_error_classifier_missing_field.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: classifier field 'format' is not a field of 'VinylRecordEntity'
```

VinylRecordEntity has media but no format field. A property or ClassVar with that name would not count as a Pydantic model field either.

**Repair.** Change the marker field argument back to media. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## The classifier names the relation itself

In the preparation, replace this declaration text:

```python
Classifier(field="media",
```

with:

```python
Classifier(field="pressing",
```

[Script](../../examples/step_21_relations/28_error_classifier_self.py) · [Notebook](../../examples/step_21_relations/28_error_classifier_self.ipynb)


```bash
uv run python examples/step_21_relations/28_error_classifier_self.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: the classifier field names the specialization field itself
```

The code must be stored in a separate field. pressing stores the relation container itself.

**Repair.** Use the existing media field as classifier. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## The reverse field name disagrees

In the preparation, replace this declaration text:

```python
Inverse(field_name="record")
```

with:

```python
Inverse(field_name="album")
```

[Script](../../examples/step_21_relations/29_error_inverse_name.py) · [Notebook](../../examples/step_21_relations/29_error_inverse_name.ipynb)


```bash
uv run python examples/step_21_relations/29_error_inverse_name.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: alternative 'FirstPressEntity' points back through 'record', but the axis names 'album'
```

The head asks for a field called album, while each alternative declares record.

**Repair.** Change the head marker back to Inverse(field_name="record"). After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## An alternative has no reverse declaration

In the preparation, replace this declaration text:

```python
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")
```

with nothing: remove just that marker or field declaration. Leave the other declarations unchanged.

[Script](../../examples/step_21_relations/30_error_no_reverse.py) · [Notebook](../../examples/step_21_relations/30_error_no_reverse.ipynb)


```bash
uv run python examples/step_21_relations/30_error_no_reverse.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: code(s) ['first'] are named by the head but no alternative declares them
```

Without its reverse declaration FirstPressEntity contributes no code. The reported missing first code is a consequence of the removed field.

**Repair.** Restore the complete FirstPressEntity.record declaration shown in the correct model. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## An alternative has two reverse fields

On `FirstPressEntity`, add this complete field after `stamper`, leaving the existing `record` field unchanged:

```python
    other_record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("other_record", Literal["first"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Second reverse field")
```

[Script](../../examples/step_21_relations/31_error_two_reverse_fields.py) · [Notebook](../../examples/step_21_relations/31_error_two_reverse_fields.ipynb)


```bash
uv run python examples/step_21_relations/31_error_two_reverse_fields.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: alternative 'FirstPressEntity' points back through more than one field (other_record, record); the axis cannot tell which one declares its code
```

Two Generalization fields on FirstPressEntity point at the same head. The validator requires one reverse field for that head.

**Repair.** Remove other_record. If a separate ordinary reference is needed, model it as an ordinary association rather than a second Generalization. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## An alternative is not declared as an entity

In the preparation, replace this declaration text:

```python
@entity(description="First pressing", domain=MusicDomain)
```

with nothing: remove just that marker or field declaration. Leave the other declarations unchanged.

[Script](../../examples/step_21_relations/32_error_undeclared_entity.py) · [Notebook](../../examples/step_21_relations/32_error_undeclared_entity.ipynb)


```bash
uv run python examples/step_21_relations/32_error_undeclared_entity.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: alternative 'FirstPressEntity' is not a declared entity — mark it with @entity
```

Inheriting BaseEntity supplies the value behaviour but does not register the class as a declared entity.

**Repair.** Restore the @entity decorator on FirstPressEntity. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## Two axes use the same classifier

For this and the later different-set experiment, start from a working two-axis model. Replace the head class in the shared preparation with the complete class below. Keep the three alternatives unchanged. `reported_media` holds another catalogue's code; `reported_pressing` uses the same alternatives as `pressing`. Both axes share the existing reverse field.

```python
@entity(description="Vinyl record", domain=MusicDomain)
class VinylRecordEntity(BaseEntity):
    """Describe the information shared by all pressings."""

    id: str = Field(description="Record identifier")
    title: str = Field(description="Album title")
    media: str = Field(description="Pressing code")
    reported_media: str = Field(description="Pressing code reported by another catalogue")
    reported_pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="reported_media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Pressing reported by another catalogue")
    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")
```

The success check still prints `Corrected model built`. Now introduce just the classifier mistake below.

In the preparation, replace this declaration text:

```python
Classifier(field="reported_media",
```

with:

```python
Classifier(field="media",
```

[Script](../../examples/step_21_relations/33_error_shared_classifier.py) · [Notebook](../../examples/step_21_relations/33_error_shared_classifier.ipynb)


```bash
uv run python examples/step_21_relations/33_error_shared_classifier.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: classifier field 'media' already decides 'VinylRecordEntity.reported_pressing'
```

The second axis reuses media. Each axis on one head must name its own classifier field.

**Repair.** Restore reported_media on reported_pressing. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## Two heads claim the same alternative

Insert this additional class and its rebuild call immediately before the shared preparation's final `for model in (...)` loop:

```python

@entity(description="Another record", domain=MusicDomain)
class OtherRecordEntity(BaseEntity):
    """Demonstrate a second head claiming the same alternatives."""

    id: str = Field(description="Record identifier")
    media: str = Field(description="Pressing code")
    pressing: Annotated[
        Specialization[FirstPressEntity | RepressEntity | TestPressEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="Details of this pressing")

OtherRecordEntity.model_rebuild()
```

[Script](../../examples/step_21_relations/34_error_two_heads.py) · [Notebook](../../examples/step_21_relations/34_error_two_heads.ipynb)


```bash
uv run python examples/step_21_relations/34_error_two_heads.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: class 'FirstPressEntity' is an alternative of 'OtherRecordEntity.pressing' and of 'VinylRecordEntity.pressing'
```

The same alternative class has been put under two different heads. This is checked across declarations, before inspecting each individual axis.

**Repair.** Remove OtherRecordEntity, or model a different domain concept using its own alternative classes. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## A reverse declaration is outside the union

Insert this additional class and its rebuild call immediately before the shared preparation's final `for model in (...)` loop:

```python

@entity(description="An unlisted pressing", domain=MusicDomain)
class UnlistedPressEntity(BaseEntity):
    """Demonstrate an alternative omitted from the head."""

    id: str = Field(description="Pressing identifier")
    record: Annotated[
        Generalization[VinylRecordEntity],
        Classifier("record", Literal["unlisted"]),
        Inverse(VinylRecordEntity, "pressing"),
    ] = Rel(description="Record described by this pressing")

UnlistedPressEntity.model_rebuild()
```

[Script](../../examples/step_21_relations/35_error_outside_alternative.py) · [Notebook](../../examples/step_21_relations/35_error_outside_alternative.ipynb)


```bash
uv run python examples/step_21_relations/35_error_outside_alternative.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: class 'UnlistedPressEntity' points at 'pressing' without being named in the union — add it to the alternatives or remove its reverse field
```

The loaded UnlistedPressEntity declaration points at VinylRecordEntity but is absent from its alternatives. The validator discovers loaded declared classes, not just classes reachable from the head union.

**Repair.** Remove this unintended class. To make it a supported alternative instead, add both its class and unlisted code to the head. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## A relation is used as classifier

In the preparation, replace this declaration text:

```python
media: str = Field(description="Pressing code")
```

with:

```python
media: AssociationOne[FirstPressEntity] = Rel(description="A relation cannot supply the code")
```

Also import `AssociationOne` from `aoa.action_machine.domain` to make the deliberately wrong type available.

[Script](../../examples/step_21_relations/36_error_relation_classifier.py) · [Notebook](../../examples/step_21_relations/36_error_relation_classifier.ipynb)


```bash
uv run python examples/step_21_relations/36_error_relation_classifier.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordEntity' is invalid: classifier field 'media' is a relation, not a scalar field
```

media now holds a relation container rather than an ordinary code value. The declaration validator refuses an ownership relation as the classifier.

**Repair.** Restore media: str with its Field description. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## Two entities form a specialization cycle

This experiment uses two small classes so the cycle is easy to see. Its valid starting point has only the `AEntity.detail` → `BEntity` relationship and the reverse `BEntity.back`. The broken version below adds the opposite specialization, `BEntity.detail` → `AEntity`, with `AEntity.back` as its reverse. That is one additional relationship, declared on both sides. The codes agree, so the error isolates the cycle rather than a code mismatch. Use this complete preparation instead of the catalogue model:

```python
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Classifier, Generalization, Inverse, Rel, Specialization
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class MusicDomain(BaseDomain):
    """Group the cycle experiment."""

    name = "music"
    description = "Cycle experiment"


@entity(description="First level", domain=MusicDomain)
class AEntity(BaseEntity):
    """Declare the first level of detail."""

    id: str = Field(description="Identifier")
    kind: str = Field(description="Detail code")
    detail: Annotated[Specialization[BEntity], Classifier("kind", Literal["b"]), Inverse(field_name="back")] = Rel(
        description="Next level"
    )
    back: Annotated[Generalization[BEntity], Classifier("back", Literal["a"]), Inverse(BEntity, "detail")] = Rel(
        description="Return to B"
    )


@entity(description="Second level", domain=MusicDomain)
class BEntity(BaseEntity):
    """Declare the second level of detail."""

    id: str = Field(description="Identifier")
    kind: str = Field(description="Detail code")
    back: Annotated[Generalization[AEntity], Classifier("back", Literal["b"]), Inverse(AEntity, "detail")] = Rel(
        description="Return to A"
    )
    detail: Annotated[Specialization[AEntity], Classifier("kind", Literal["a"]), Inverse(field_name="back")] = Rel(
        description="Next level"
    )


AEntity.model_rebuild()
BEntity.model_rebuild()
```

[Script](../../examples/step_21_relations/37_error_cycle.py) · [Notebook](../../examples/step_21_relations/37_error_cycle.ipynb)


```bash
uv run python examples/step_21_relations/37_error_cycle.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'detail' on entity 'AEntity' is invalid: the head and its alternatives form a cycle: AEntity -> BEntity -> AEntity
```

The codes agree on both relationships, but following detail leads from A to B and back to A. This real two-class model reaches the cycle check.

**Repair.** Remove the B-to-A specialization: remove BEntity.detail and its reverse AEntity.back. A-to-B remains valid. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## A second axis has a different alternative set

Start from the working two-axis head shown under [Two axes use the same classifier](#two-axes-use-the-same-classifier), before its intentional error. Keep the distinct `media` and `reported_media` fields. On `reported_pressing`, replace the two declarations with:

```python
Specialization[FirstPressEntity | RepressEntity],
Classifier(field="reported_media", codes=Literal["first", "repress"]),
```

These are the first two entries inside that field's `Annotated` declaration; keep its `Inverse` and `Rel` unchanged. The first axis still lists all three alternatives.

[Script](../../examples/step_21_relations/38_error_axis_subset.py) · [Notebook](../../examples/step_21_relations/38_error_axis_subset.ipynb)


```bash
uv run python examples/step_21_relations/38_error_axis_subset.py
```

Actual output:

```text
SpecializationDeclarationError: Specialization 'reported_pressing' on entity 'VinylRecordEntity' is invalid: class 'TestPressEntity' points at 'reported_pressing' without being named in the union — add it to the alternatives or remove its reverse field
```

TestPressEntity still points at VinylRecordEntity. The current closure check compares that reverse link with every axis on the head, so it rejects TestPressEntity as outside reported_pressing. Distinct classifier fields alone are not sufficient.

**Repair.** Restore the shared alternative set, or use separate heads when the two choices need different sets. This example documents a current restriction; it does not implement a workaround in the framework. After applying it, use the success-check block instead of the refusal-check block; it prints:

```text
Corrected model built
```

## Machine creation reports KeyError

The direct validator is not the first operation in a full machine build. Some graph edges and their display labels are constructed earlier. To observe the consequence, use the same single change as [A head code has no matching alternative](#a-head-code-has-no-matching-alternative): change the head's `first` code to `early` while leaving the alternatives unchanged. This time call the machine constructor:

[Script](../../examples/step_21_relations/39_error_machine_build.py) · [Notebook](../../examples/step_21_relations/39_error_machine_build.ipynb)


```python
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

try:
    ActionProductMachine(loggers=[])
except KeyError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The broken model built")
```


```bash
uv run python examples/step_21_relations/39_error_machine_build.py
```

Actual output:

```text
KeyError: 'early'
```

The same declaration as example 23 reaches graph-edge construction during machine creation. That path tries to assemble labels before the declaration validator runs and raises KeyError for early. Calling the declaration validator directly, as the diagnostic examples do, provides the specific missing-code message. This is a current build-order limitation.

Restore `first` on the head and the machine builds. An unexplained `KeyError` here is therefore not evidence that the data store lost a row. Check the declarations with the direct validator before investigating application data.

## Marker arguments fail before a build

The `Classifier` object also validates its own arguments when Python evaluates the annotation. These failures precede declaration comparison. The following independent experiments each make one invalid call and then its corrected call; none needs the catalogue model.

### An empty classifier field name

[Script](../../examples/step_21_relations/40_error_classifier_name.py) · [Notebook](../../examples/step_21_relations/40_error_classifier_name.ipynb)


```python
from typing import Literal

from aoa.action_machine.domain import Classifier

try:
    Classifier("", Literal["first"])
except ValueError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid marker was accepted")

marker = Classifier("media", Literal["first"])
print("Corrected:", marker.code_values)
```


```bash
uv run python examples/step_21_relations/40_error_classifier_name.py
```

Actual output:

```text
ValueError: Classifier: field cannot be empty or whitespace-only.
Corrected: ('first',)
```

The marker rejects this argument immediately. The corrected constructor at the end succeeds; no graph or database is involved.

### Codes must be written as a Literal

[Script](../../examples/step_21_relations/41_error_codes_not_literal.py) · [Notebook](../../examples/step_21_relations/41_error_codes_not_literal.ipynb)


```python
from typing import Literal

from aoa.action_machine.domain import Classifier

try:
    Classifier("media", ["first"])
except TypeError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid marker was accepted")

marker = Classifier("media", Literal["first"])
print("Corrected:", marker.code_values)
```


```bash
uv run python examples/step_21_relations/41_error_codes_not_literal.py
```

Actual output:

```text
TypeError: Classifier: codes must be a Literal of codes, got list: ['first'].
Corrected: ('first',)
```

The marker rejects this argument immediately. The corrected constructor at the end succeeds; no graph or database is involved.

### A code must be a string

[Script](../../examples/step_21_relations/42_error_code_type.py) · [Notebook](../../examples/step_21_relations/42_error_code_type.ipynb)


```python
from typing import Literal

from aoa.action_machine.domain import Classifier

try:
    Classifier("media", Literal[1])
except TypeError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid marker was accepted")

marker = Classifier("media", Literal["first"])
print("Corrected:", marker.code_values)
```


```bash
uv run python examples/step_21_relations/42_error_code_type.py
```

Actual output:

```text
TypeError: Classifier: codes must be str, got int: 1.
Corrected: ('first',)
```

The marker rejects this argument immediately. The corrected constructor at the end succeeds; no graph or database is involved.

### A code must not be blank

[Script](../../examples/step_21_relations/43_error_empty_code.py) · [Notebook](../../examples/step_21_relations/43_error_empty_code.ipynb)


```python
from typing import Literal

from aoa.action_machine.domain import Classifier

try:
    Classifier("media", Literal[" "])
except ValueError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid marker was accepted")

marker = Classifier("media", Literal["first"])
print("Corrected:", marker.code_values)
```


```bash
uv run python examples/step_21_relations/43_error_empty_code.py
```

Actual output:

```text
ValueError: Classifier: codes cannot contain an empty or whitespace-only code.
Corrected: ('first',)
```

The marker rejects this argument immediately. The corrected constructor at the end succeeds; no graph or database is involved.

## A valid declaration can still accompany inconsistent data

A successful build is not a data-integrity audit. The [unknown-code experiment](../../examples/step_21_relations/07_specialization_data_codes.py) accepts `variant="unknown"`; the [mismatched-object experiment](../../examples/step_21_relations/08_specialization_mismatched_data.py) accepts a `RepressEntity` labelled `first`. These examples identify checks that the application's loading layer must perform. They do not describe automatic fallback to “no relation”.

For construction failures unrelated to declaration matching, see the tutorial's [wrong-object experiment](../tutorials/step-21-relations.md#rejecting-an-unrelated-object) and [immutable-link experiment](../tutorials/step-21-relations.md#replacing-a-link-instead-of-changing-it). Those failures are Pydantic `ValidationError` results, not `SpecializationDeclarationError`.

The [reference](../reference/intents-and-invariants.md#entity-specialization-the-build-rules) records the exact scope of current validation, including inverse-marker and multiple-axis limitations.
