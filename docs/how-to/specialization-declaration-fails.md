# Diagnosing a specialization declaration

A **head** contains common information; an **alternative** contains data specific to
one kind of that same object. An **axis** is one head field, its dictionary and its
alternatives. If these terms are new, begin with the
[complete working model](../tutorials/step-21-relations.md#declare-the-complete-model).

The supported declaration has two parts. The head uses
`Specialization[Alternatives, Dictionary]`. Each alternative has a `Generalization[Head]`
field marked with `Classifier(field="record", variant=Dictionary.VALUE)`.
The marker belongs on the reverse field whose name it states. The dictionary supplies
the entire vocabulary, and every value must have exactly one alternative.

Each example below changes one condition. Its script and notebook contain the complete
model and the expected failure. Run each separately with `uv run python <script-path>`;
loading several broken models in one process changes the set of declarations being checked.
The declaration examples call the validator directly so that graph expansion cannot mask
the intended diagnostic. Normal machine creation also performs declaration validation,
but an invalid model can fail earlier during graph construction.

## Check the declaration form first

Import `value` from `aoa.action_machine.domain` and write dictionary members as
`FIRST = value(code="first", display_name="First")`. The removed class-name alias can
fail before specialization validation even runs. A mutable or unsupported dictionary
property annotation also fails when its class is created; use the
[dictionary refusal examples](../tutorials/step-20-dictionaries.md#read-a-refusal-as-a-specific-contract-violation)
to distinguish that error from a missing alternative or an incorrect reverse relationship.


## Declaration failures

### The second argument must be a dictionary

Use str as the second type argument.

[Script](../../examples/step_21_relations/20_error_missing_classifier.py) · [Notebook](../../examples/step_21_relations/20_error_missing_classifier.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: is a specialization container whose second type argument is not a closed dictionary; write Specialization[Alternatives, Dictionary]
```

Replace str with a nonempty decorated BaseEnumEntity descendant. Omitting the second argument entirely fails earlier with TypeError.

### An alternative must name a value

Leave the first pressing's reverse field without Classifier.

[Script](../../examples/step_21_relations/21_error_missing_code.py) · [Notebook](../../examples/step_21_relations/21_error_missing_code.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: alternative 'FirstPressSpecEntity' names no value of 'VinylRecordKindEnumEntity' — write Classifier(field=..., variant=VinylRecordKindEnumEntity.<VALUE>)
```

Add Classifier(field="record", variant=VinylRecordKindEnumEntity.FIRST). A reverse link alone does not state which dictionary value selects this class.

### Every dictionary value needs an alternative

Add lost to the dictionary without adding its alternative.

[Script](../../examples/step_21_relations/23_error_unknown_head_code.py) · [Notebook](../../examples/step_21_relations/23_error_unknown_head_code.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: code(s) ['lost'] are named by the head but no alternative declares them
```

Add the corresponding alternative and its marker, or choose a dictionary that describes exactly the alternatives of this axis. An axis borrows the entire vocabulary.

### Two alternatives cannot share one value

Give two alternative classes the same dictionary value.

[Script](../../examples/step_21_relations/25_error_duplicate_code.py) · [Notebook](../../examples/step_21_relations/25_error_duplicate_code.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: the head names 2 code(s) for 3 alternative(s): every alternative needs exactly one code
```

Each value must select exactly one class. The current validator first reports the count mismatch in this fixture; it does not infer another value for the second class.

### The inverse name must match

The head names album while alternatives point back through record.

[Script](../../examples/step_21_relations/29_error_inverse_name.py) · [Notebook](../../examples/step_21_relations/29_error_inverse_name.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: alternative 'FirstPressSpecEntity' points back through 'record', but the axis names 'album'
```

Make Inverse(field_name="record") agree with the actual Generalization field. This is the paired relationship, not a database column.

### An alternative needs a reverse declaration

Remove the first pressing's Generalization field.

[Script](../../examples/step_21_relations/30_error_no_reverse.py) · [Notebook](../../examples/step_21_relations/30_error_no_reverse.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: code(s) ['first'] are named by the head but no alternative declares them
```

Restore the reverse field and its Classifier. Without it the head's first value has no mapped alternative, even though the class remains in the union.

### Two reverse fields are ambiguous

Give one alternative two Generalization fields pointing to the same head.

[Script](../../examples/step_21_relations/31_error_two_reverse_fields.py) · [Notebook](../../examples/step_21_relations/31_error_two_reverse_fields.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: alternative 'FirstPressSpecEntity' points back through more than one field (other_record, record); the axis cannot tell which one declares its code
```

Keep one reverse field to this head. The declaration cannot choose which of two reverse fields supplies the alternative's value.

### The alternative must be registered

Leave FirstPressSpecEntity without @entity.

[Script](../../examples/step_21_relations/32_error_undeclared_entity.py) · [Notebook](../../examples/step_21_relations/32_error_undeclared_entity.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: alternative 'FirstPressSpecEntity' is not a declared entity — mark it with @entity
```

Decorate the class with its description and domain. Being a Python subclass of BaseSpecEntity does not register an Entity node.

### An alternative belongs to one head

List the same alternative class under two different heads.

[Script](../../examples/step_21_relations/34_error_two_heads.py) · [Notebook](../../examples/step_21_relations/34_error_two_heads.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: class 'FirstPressSpecEntity' is an alternative of 'OtherRecordCoreEntity.pressing' and of 'VinylRecordCoreEntity.pressing'
```

Declare distinct alternative classes for the distinct heads. Reusing a dictionary is allowed; reusing one alternative as the data of two different head types is not.

### A reverse link must belong to the declared axis

Add a class pointing at the head without listing it among the alternatives.

[Script](../../examples/step_21_relations/35_error_outside_alternative.py) · [Notebook](../../examples/step_21_relations/35_error_outside_alternative.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: class 'UnlistedPressSpecEntity' points at 'pressing' without being named in the union — add it to the alternatives or remove its reverse field
```

Include the class and give it an appropriate dictionary value, or remove that reverse specialization declaration.

### Specialization cannot form a cycle

Make two classes specialize one another.

[Script](../../examples/step_21_relations/37_error_cycle.py) · [Notebook](../../examples/step_21_relations/37_error_cycle.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'detail' on entity 'ASpecEntity' is invalid: the head and its alternatives form a cycle: ASpecEntity -> BSpecEntity -> ASpecEntity
```

The chain returns to a class already visited, so it cannot describe a direction from common to more specific data. Remove the cyclic relationship.

### A second axis cannot omit a reverse-linked class

The second axis covers a smaller set than the classes pointing at this head.

[Script](../../examples/step_21_relations/38_error_axis_subset.py) · [Notebook](../../examples/step_21_relations/38_error_axis_subset.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'reported_pressing' on entity 'VinylRecordCoreEntity' is invalid: class 'TestPressSpecEntity' points at 'reported_pressing' without being named in the union — add it to the alternatives or remove its reverse field
```

The current closure check examines reverse links by head class. Each axis must include those alternatives. Independent disjoint alternative sets on the same head remain unsupported.

### Classifier accepts a value, not a list

Pass a list of code strings to Classifier.

[Script](../../examples/step_21_relations/41_error_codes_not_literal.py) · [Notebook](../../examples/step_21_relations/41_error_codes_not_literal.ipynb)

Output:

```text
TypeError: Classifier: variant must be a declared dictionary value, got list: ['first'].
A dictionary value, not a code list: vinyl
Declared: ['vinyl']
```

Write Classifier(field="record", variant=MediaKindEnumEntity.VINYL). The marker belongs to the reverse link; the head names the dictionary in its type argument.

### A head-side Classifier is refused

The head already identifies the dictionary in its type argument.

[Script](../../examples/step_21_relations/44_error_head_classifier.py) · [Notebook](../../examples/step_21_relations/44_error_head_classifier.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: the head must not carry Classifier; write Specialization[Alternatives, Dictionary]
```

Remove the Classifier from the head. Classifier belongs on each alternative's Generalization field, where it names that alternative's declared value.

### Classifier must name its own reverse field

The marker is on record but says the reverse field is missing.

[Script](../../examples/step_21_relations/45_error_marker_field.py) · [Notebook](../../examples/step_21_relations/45_error_marker_field.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: Classifier on 'FirstPressSpecEntity.record' names 'missing', but must name its reverse field 'record'
```

Change field="missing" to field="record". This argument names the Generalization field on the alternative; it does not name a scalar selector on the head.

### An axis cannot borrow an empty dictionary

An empty intermediate is a legal Python class but cannot supply an axis vocabulary.

[Script](../../examples/step_21_relations/46_error_empty_dictionary.py) · [Notebook](../../examples/step_21_relations/46_error_empty_dictionary.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: 'EmptyKindEnumEntity' declares no values; an axis cannot borrow codes from an empty dictionary
```

Name a decorated dictionary that declares at least one value, and supply exactly one alternative per value.

### A foreign value is refused

The alternative names a different dictionary's FIRST, even though its code is also first.

[Script](../../examples/step_21_relations/47_error_foreign_value.py) · [Notebook](../../examples/step_21_relations/47_error_foreign_value.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: alternative 'FirstPressSpecEntity' names a value OtherKindEnumEntity(code='first', display_name='Other first') that 'VinylRecordKindEnumEntity' does not declare
```

A value belongs to one dictionary. Equal code text does not make values interchangeable; select the attribute of the dictionary named by the head.

### A copied declaration is refused

The alternative constructs a new object instead of naming the declared FIRST.

[Script](../../examples/step_21_relations/48_error_copied_value.py) · [Notebook](../../examples/step_21_relations/48_error_copied_value.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: alternative 'FirstPressSpecEntity' names a value VinylRecordKindEnumEntity(code='first', display_name='First') that 'VinylRecordKindEnumEntity' does not declare
```

Use VinylRecordKindEnumEntity.FIRST. Constructing an equal object neither adds a member nor gives it the identity of a declared value.

### The dictionary must be registered

The vocabulary has values, but its class lacks @entity.

[Script](../../examples/step_21_relations/49_error_unregistered_dictionary.py) · [Notebook](../../examples/step_21_relations/49_error_unregistered_dictionary.ipynb)

Output:

```text
SpecializationDeclarationError: Specialization 'pressing' on entity 'VinylRecordCoreEntity' is invalid: 'VinylRecordKindEnumEntity' is a dictionary but not an @entity; the graph would have no node for it
```

Add @entity with the dictionary's description and domain. Values alone do not register the class in the model graph.

### Specialization requires both type arguments

Try the retired one-argument container form.

[Script](../../examples/step_21_relations/50_error_one_argument.py) · [Notebook](../../examples/step_21_relations/50_error_one_argument.ipynb)

Output:

```text
TypeError: Too few arguments for <class 'aoa.action_machine.domain.specialization_containers.Specialization'>; actual 1, expected at least 2
```

The type itself requires a dictionary argument. This fails before graph build; write Specialization[Alternatives, Dictionary].

## Invalid runtime values

A valid model does not make every incoming value valid. These separate experiments
exercise normal container construction, where errors are Pydantic `ValidationError`s.

### A bare variant code is refused

A string cannot fill the dictionary-typed variant field.

[Script](../../examples/step_21_relations/18_specialization_bare_code.py) · [Notebook](../../examples/step_21_relations/18_specialization_bare_code.ipynb)

```python
from pydantic import ValidationError

try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1", variant="first"
    )
except ValidationError as error:
    print(error.errors()[0]["msg"])
else:
    raise AssertionError("A bare code was accepted")
```

Output:

```text
Value error, VinylRecordKindEnumEntity: a bare code is not accepted; pass the declared value or its reference object {'code', 'display_name', 'properties'}.
```

Even a known code must be resolved explicitly or wrapped in a reference object. This keeps storage representation separate from the declared value used in memory.

### An unknown variant is refused

Pass a reference whose code is unknown after a successful model build.

[Script](../../examples/step_21_relations/07_specialization_data_codes.py) · [Notebook](../../examples/step_21_relations/07_specialization_data_codes.ipynb)

```python
ActionProductMachine(loggers=[])
try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1",
        variant={"code": "unknown"},
    )
except ValidationError as error:
    print("Refused:", error.errors()[0]["msg"])
else:
    raise AssertionError("A case the example exists to refuse was accepted")
```

Output:

```text
Refused: Value error, 'unknown' is not a declared value of VinylRecordKindEnumEntity. Declared: ['first', 'repress', 'test'].
```

The build checks declarations; constructing the container checks the incoming value. An unknown code is not a legitimate unloaded or absent variant.

### An unrelated loaded object is refused

Pass the head record where pressing details are required.

[Script](../../examples/step_21_relations/06_specialization_wrong_type.py) · [Notebook](../../examples/step_21_relations/06_specialization_wrong_type.ipynb)

```python
from pydantic import ValidationError

record = VinylRecordCoreEntity(
    id="rec-1",
    title="Kind of Blue",
    pressing=Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
    ),
)
try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
        entity=record,
    )
except ValidationError as error:
    print(type(error).__name__)
    print(sorted({item["type"] for item in error.errors()}))
else:
    raise AssertionError("An unrelated entity was accepted")
```

Output:

```text
ValidationError
['model_type']
```

The first type argument checks which object classes can fill entity. The head is outside that union, so Pydantic reports model_type. This is different from a permitted alternative paired with the wrong value.

### The loaded class must match the value

Pair FIRST with an otherwise valid RepressSpecEntity.

[Script](../../examples/step_21_relations/08_specialization_mismatched_data.py) · [Notebook](../../examples/step_21_relations/08_specialization_mismatched_data.ipynb)

```python
repress = RepressSpecEntity(
    id="rec-1",
    year=1997,
    record=Generalization[VinylRecordCoreEntity](id="rec-1"),
)
try:
    Specialization[FirstPressSpecEntity | RepressSpecEntity | TestPressSpecEntity, VinylRecordKindEnumEntity](
        id="rec-1",
        variant=VinylRecordKindEnumEntity.FIRST,
        entity=repress,
    )
except ValidationError as error:
    print("Refused:", error.errors()[0]["msg"])
else:
    raise AssertionError("A case the example exists to refuse was accepted")
```

Output:

```text
Refused: Value error, variant 'first' does not match RepressSpecEntity, which declares 'repress'
```

The entity type belongs to the union, but its declared value is REPRESS. The container rejects the pair. Matching uses the declared value's identity, so equal codes from different dictionaries cannot substitute for one another.

## Migrating from code-list declarations

Remove the head's old `Classifier(..., codes=Literal[...])` and its duplicated selector.
Declare a dictionary, name it as the second container argument, and replace each
alternative's code list with `variant=Dictionary.VALUE`. Resolve database codes at the
resource boundary. `Classifier` has no `codes` argument, and a one-argument `Specialization`
is rejected at type construction.

This guide does not promise that arbitrary unrelated scalar fields are forbidden on a
head. The supported classification is expressed by the dictionary and the container;
ordinary domain fields retain their own meaning. Other uses of Python `Literal` elsewhere
in an application are unaffected.
