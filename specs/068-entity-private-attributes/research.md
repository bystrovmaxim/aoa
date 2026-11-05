# Research: An entity reads its private attributes

## R1. Handing the name to Pydantic

Pydantic defines `BaseModel.__getattr__` only under `if not TYPE_CHECKING:`, so `super().__getattr__(name)` runs but a type checker reports `"__getattr__" undefined in superclass`. The lookup is taken from the class at run time instead: `getattr(BaseModel, _PYDANTIC_LOOKUP)(self, name)`, with the name in a module constant. `getattr` returns `Any`, so mypy needs no comment, and Pydantic keeps its own lookup — private attributes, and its own `AttributeError` for anything else.

**Alternatives considered**: `super().__getattr__` with `# type: ignore` — refused, the repository carries no such comments; reading `__pydantic_private__` here — refused, a copy of Pydantic's lookup.
