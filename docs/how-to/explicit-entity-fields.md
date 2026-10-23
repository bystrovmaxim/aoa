# Declare entity fields explicitly

An entity-typed field must say whether it links to another object or embeds a snapshot. Previously, bare structural entity types could become ordinary fields without a relation edge. The graph now refuses these declarations. Use a relation container to model a link, or `NoRelation("reason")` to explain why a structural entity is stored as a value.

Relation descriptions belong in Pydantic `Field` metadata. To migrate an old description default, import `Field` from `pydantic` and use `Field(description="...")`. The former description carrier is no longer exported. Supply the relation when constructing the entity. Only a nullable relation with explicit `default=None` may be omitted. Descriptions and defaults are checked when the graph is built, rather than when `Field` is constructed.

| Declaration | Graph build | Construction |
| --- | --- | --- |
| Container with description, no default | Accepted | Value required |
| Nullable container with description, no default | Accepted | Value required; may be None |
| Nullable container with description and default=None | Accepted | May be omitted |
| Non-nullable container with default=None | Refused | Not reached |
| Container with a factory or another default | Refused | Not reached |
| Bare structural entity or collection | Refused | Not reached |
| Structural entity with NoRelation and a reason | Accepted | Embedded value |

The examples below use fresh processes because creating a machine discovers loaded entity declarations.

## A relation value must be supplied.

[Script](../../examples/step_21_relations/52_required_relation.py) · [Notebook](../../examples/step_21_relations/52_required_relation.ipynb)

```python
"""A relation value must be supplied.
Run: .venv/bin/python examples/step_21_relations/52_required_relation.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(description="Target")

def main() -> None:
    """Run the example and assert its result."""
    ActionProductMachine(loggers=[])
    item = HostCoreEntity(target=AssociationOne[TargetCoreEntity](id="t"))
    print("Related identifier:", item.target.id)
    assert item.target.id == "t"
    from pydantic import ValidationError
    try:
        HostCoreEntity()
    except ValidationError as error:
        print(type(error).__name__ + ": " + error.errors()[0]["msg"])
        assert error.errors()[0]["type"] == "missing"
    else:
        raise AssertionError("An omitted required relation was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
Related identifier: t
ValidationError: Field required
```

## A nullable relation may be omitted only with an explicit default.

[Script](../../examples/step_21_relations/53_optional_relation.py) · [Notebook](../../examples/step_21_relations/53_optional_relation.ipynb)

```python
"""A nullable relation may be omitted only with an explicit default.
Run: .venv/bin/python examples/step_21_relations/53_optional_relation.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity] | None, NoInverse()] = Field(default=None, description="Target")

def main() -> None:
    """Run the example and assert its result."""
    ActionProductMachine(loggers=[])
    item = HostCoreEntity()
    print("Omitted relation:", item.target)
    assert item.target is None

if __name__ == "__main__":
    main()
```

Actual output:

```text
Omitted relation: None
```

## An embedded entity explicitly opts out of a relation.

[Script](../../examples/step_21_relations/54_embedded_entity.py) · [Notebook](../../examples/step_21_relations/54_embedded_entity.ipynb)

```python
"""An embedded entity explicitly opts out of a relation.
Run: .venv/bin/python examples/step_21_relations/54_embedded_entity.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[TargetCoreEntity, NoRelation("Stored snapshot")] = Field(description="Snapshot")

def main() -> None:
    """Run the example and assert its result."""
    ActionProductMachine(loggers=[])
    item = HostCoreEntity(target=TargetCoreEntity(id="t"))
    print("Embedded identifier:", item.target.id)
    assert item.target.id == "t"

if __name__ == "__main__":
    main()
```

Actual output:

```text
Embedded identifier: t
```

## A bare structural entity is refused when the graph is built.

[Script](../../examples/step_21_relations/55_bare_entity_refused.py) · [Notebook](../../examples/step_21_relations/55_bare_entity_refused.ipynb)

```python
"""A bare structural entity is refused when the graph is built.
Run: .venv/bin/python examples/step_21_relations/55_bare_entity_refused.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: TargetCoreEntity = Field(description="Target")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == 'EntityFieldDeclarationError: Field \'target\' on entity \'HostCoreEntity\' is invalid: the field\'s type is an entity (TargetCoreEntity), so the field cannot be a scalar. Declare it as a relation (Annotated[AssociationOne[TargetCoreEntity], Inverse(...)]) or as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).'
        assert type(error).__name__ + ": " + str(error) == 'EntityFieldDeclarationError: Field \'target\' on entity \'HostCoreEntity\' is invalid: the field\'s type is an entity (TargetCoreEntity), so the field cannot be a scalar. Declare it as a relation (Annotated[AssociationOne[TargetCoreEntity], Inverse(...)]) or as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).'
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: the field's type is an entity (TargetCoreEntity), so the field cannot be a scalar. Declare it as a relation (Annotated[AssociationOne[TargetCoreEntity], Inverse(...)]) or as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).
```

## A relation needs a non-blank description.

[Script](../../examples/step_21_relations/56_relation_description.py) · [Notebook](../../examples/step_21_relations/56_relation_description.ipynb)

```python
"""A relation needs a non-blank description.
Run: .venv/bin/python examples/step_21_relations/56_relation_description.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(description=" ")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == 'EntityFieldDeclarationError: Field \'target\' on entity \'HostCoreEntity\' is invalid: a relation field needs a non-blank description; write it as Field(description="...").'
        assert type(error).__name__ + ": " + str(error) == 'EntityFieldDeclarationError: Field \'target\' on entity \'HostCoreEntity\' is invalid: a relation field needs a non-blank description; write it as Field(description="...").'
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: a relation field needs a non-blank description; write it as Field(description="...").
```

## A relation cannot obtain its value from a factory.

[Script](../../examples/step_21_relations/57_relation_factory.py) · [Notebook](../../examples/step_21_relations/57_relation_factory.ipynb)

```python
"""A relation cannot obtain its value from a factory.
Run: .venv/bin/python examples/step_21_relations/57_relation_factory.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(default_factory=lambda: AssociationOne(id="t"), description="Target")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: a relation field cannot use default_factory; supply the value, or declare default=None on a nullable relation."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: a relation field cannot use default_factory; supply the value, or declare default=None on a nullable relation."
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: a relation field cannot use default_factory; supply the value, or declare default=None on a nullable relation.
```

## A non-nullable relation cannot default to None.

[Script](../../examples/step_21_relations/58_relation_null_default.py) · [Notebook](../../examples/step_21_relations/58_relation_null_default.ipynb)

```python
"""A non-nullable relation cannot default to None.
Run: .venv/bin/python examples/step_21_relations/58_relation_null_default.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(default=None, description="Target")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: default=None needs a nullable annotation; write Annotated[AssociationOne | None, ...] = Field(default=None, description=...)."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: default=None needs a nullable annotation; write Annotated[AssociationOne | None, ...] = Field(default=None, description=...)."
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: default=None needs a nullable annotation; write Annotated[AssociationOne | None, ...] = Field(default=None, description=...).
```

## A relation cannot have a preconstructed default.

[Script](../../examples/step_21_relations/59_relation_object_default.py) · [Notebook](../../examples/step_21_relations/59_relation_object_default.ipynb)

```python
"""A relation cannot have a preconstructed default.
Run: .venv/bin/python examples/step_21_relations/59_relation_object_default.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse()] = Field(default=AssociationOne(id="t"), description="Target")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: a relation field takes no default other than an explicit None on a nullable relation; a description belongs to Field(description=...), and the value is supplied by the caller."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: a relation field takes no default other than an explicit None on a nullable relation; a description belongs to Field(description=...), and the value is supplied by the caller."
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: a relation field takes no default other than an explicit None on a nullable relation; a description belongs to Field(description=...), and the value is supplied by the caller.
```

## A collection of structural entities needs a relation container.

[Script](../../examples/step_21_relations/60_entity_collection.py) · [Notebook](../../examples/step_21_relations/60_entity_collection.ipynb)

```python
"""A collection of structural entities needs a relation container.
Run: .venv/bin/python examples/step_21_relations/60_entity_collection.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: list[TargetCoreEntity] = Field(description="Targets")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == 'EntityFieldDeclarationError: Field \'target\' on entity \'HostCoreEntity\' is invalid: the field\'s type is a collection of an entity (list); a collection is not a relation. Declare the many relation (Annotated[AssociationMany[TargetCoreEntity], Inverse(...)]) or mark the field as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).'
        assert type(error).__name__ + ": " + str(error) == 'EntityFieldDeclarationError: Field \'target\' on entity \'HostCoreEntity\' is invalid: the field\'s type is a collection of an entity (list); a collection is not a relation. Declare the many relation (Annotated[AssociationMany[TargetCoreEntity], Inverse(...)]) or mark the field as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).'
        assert type(error).__name__ + ": " + str(error) == 'EntityFieldDeclarationError: Field \'target\' on entity \'HostCoreEntity\' is invalid: the field\'s type is a collection of an entity (list); a collection is not a relation. Declare the many relation (Annotated[AssociationMany[TargetCoreEntity], Inverse(...)]) or mark the field as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).'
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: the field's type is a collection of an entity (list); a collection is not a relation. Declare the many relation (Annotated[AssociationMany[TargetCoreEntity], Inverse(...)]) or mark the field as an embedded value (Annotated[TargetCoreEntity, NoRelation("reason")]).
```

## A relation container cannot also be an embedded value.

[Script](../../examples/step_21_relations/61_marker_on_relation.py) · [Notebook](../../examples/step_21_relations/61_marker_on_relation.ipynb)

```python
"""A relation container cannot also be an embedded value.
Run: .venv/bin/python examples/step_21_relations/61_marker_on_relation.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity], NoInverse(), NoRelation("Snapshot")] = Field(description="Target")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation container cannot be combined; keep the container, or state why no relation exists."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation container cannot be combined; keep the container, or state why no relation exists."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation container cannot be combined; keep the container, or state why no relation exists."
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation container cannot be combined; keep the container, or state why no relation exists.
```

## An embedded entity marker cannot mark a scalar.

[Script](../../examples/step_21_relations/62_marker_on_scalar.py) · [Notebook](../../examples/step_21_relations/62_marker_on_scalar.ipynb)

```python
"""An embedded entity marker cannot mark a scalar.
Run: .venv/bin/python examples/step_21_relations/62_marker_on_scalar.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[str, NoRelation("Snapshot")] = Field(description="Text")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation marks an embedded value, so it applies only to a Core, Assoc, Detail or Spec entity; this field's type is str."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation marks an embedded value, so it applies only to a Core, Assoc, Detail or Spec entity; this field's type is str."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation marks an embedded value, so it applies only to a Core, Assoc, Detail or Spec entity; this field's type is str."
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation marks an embedded value, so it applies only to a Core, Assoc, Detail or Spec entity; this field's type is str.
```

## An embedded value cannot carry relation markers.

[Script](../../examples/step_21_relations/63_conflicting_markers.py) · [Notebook](../../examples/step_21_relations/63_conflicting_markers.ipynb)

```python
"""An embedded value cannot carry relation markers.
Run: .venv/bin/python examples/step_21_relations/63_conflicting_markers.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[TargetCoreEntity, NoRelation("Snapshot"), NoInverse()] = Field(description="Target")

def main() -> None:
    """Run the example and assert its result."""
    from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
    try:
        ActionProductMachine(loggers=[])
    except EntityFieldDeclarationError as error:
        print(type(error).__name__ + ": " + str(error))
        assert error.field_name == "target"
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation marker cannot be combined; the field either has a relation or it does not."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation marker cannot be combined; the field either has a relation or it does not."
        assert type(error).__name__ + ": " + str(error) == "EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation marker cannot be combined; the field either has a relation or it does not."
    else:
        raise AssertionError("The invalid declaration was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
EntityFieldDeclarationError: Field 'target' on entity 'HostCoreEntity' is invalid: NoRelation and a relation marker cannot be combined; the field either has a relation or it does not.
```

## A nullable relation without a default must still be supplied.

[Script](../../examples/step_21_relations/64_nullable_required_relation.py) · [Notebook](../../examples/step_21_relations/64_nullable_required_relation.ipynb)

```python
"""A nullable relation without a default must still be supplied.
Run: .venv/bin/python examples/step_21_relations/64_nullable_required_relation.py
"""

from typing import Annotated
from pydantic import Field
from aoa.action_machine.domain import BaseCoreEntity, AssociationOne, NoInverse, NoRelation
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class ExampleDomain(BaseDomain):
    """Group the declarations in this example."""
    name = "example"
    description = "Explicit entity fields"

@entity(description="Related object", domain=ExampleDomain)
class TargetCoreEntity(BaseCoreEntity):
    """Identify the related object."""
    id: str = Field(description="Identifier")

@entity(description="Host object", domain=ExampleDomain)
class HostCoreEntity(BaseCoreEntity):
    """Declare the field under examination."""
    target: Annotated[AssociationOne[TargetCoreEntity] | None, NoInverse()] = Field(description="Target")

def main() -> None:
    """Run the example and assert its result."""
    ActionProductMachine(loggers=[])
    item = HostCoreEntity(target=AssociationOne[TargetCoreEntity](id="t"))
    print("Related identifier:", item.target.id)
    assert item.target.id == "t"
    from pydantic import ValidationError
    try:
        HostCoreEntity()
    except ValidationError as error:
        print(type(error).__name__ + ": " + error.errors()[0]["msg"])
        assert error.errors()[0]["type"] == "missing"
    else:
        raise AssertionError("An omitted required relation was accepted")

if __name__ == "__main__":
    main()
```

Actual output:

```text
Related identifier: t
ValidationError: Field required
```

## Boundaries

The embedded marker applies to Core, Assoc, Detail and Spec values. It does not make a collection a relation. It cannot accompany relation markers or a relation container. A state entity is represented through a lifecycle type, rather than an entity field. Dictionary references, schemas and scalar fields retain their own forms. A hidden edge still needs a valid declaration and description.

See [relation tutorial](../tutorials/step-21-relations.md), [invariants](../reference/intents-and-invariants.md), and [specialization refusals](specialization-declaration-fails.md).
