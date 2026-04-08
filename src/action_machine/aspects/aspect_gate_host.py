# src/action_machine/aspects/aspect_gate_host.py
"""
Module: AspectGateHost — marker mixin for @regular_aspect and @summary_aspect.

AspectGateHost is a marker mixin that indicates a class supports the aspect
pipeline. @regular_aspect and @summary_aspect are method-level decorators,
so they do not validate issubclass directly. The marker mixin is used for:

1. Contract documentation: AspectGateHost in a class MRO signals that the
   class supports pipeline aspects.
2. Structural validation: MetadataBuilder can verify the class inherits
   AspectGateHost before collecting aspect metadata.
3. Consistency: gate mixins such as RoleGateHost, DependencyGateHost,
   CheckerGateHost, AspectGateHost, and ConnectionGateHost are all marker
   classes without logic.

After the coordinator refactor, the mixin is purely declarative.
The decorators attach _new_aspect_meta directly to methods, and
MetadataBuilder collects aspect metadata from the class MRO.
"""


class AspectGateHost:
    """
    Маркерный миксин, обозначающий поддержку конвейера аспектов.

    Класс, наследующий AspectGateHost, может содержать методы,
    декорированные @regular_aspect и @summary_aspect. MetadataBuilder
    собирает эти методы в ClassMetadata.aspects.

    Миксин не содержит логики, полей или методов. Его единственная функция —
    документировать контракт и обеспечивать единообразие с другими
    гейт-миксинами.

    Атрибуты уровня класса (создаются динамически декораторами на методах):
        method._new_aspect_meta : dict
            Словарь {"type": "regular"|"summary", "description": "..."},
            записываемый декоратором @regular_aspect или @summary_aspect
            в сам метод. Читается MetadataBuilder при сборке
            ClassMetadata.aspects (tuple[AspectMeta, ...]).
            НЕ используется напрямую — только через ClassMetadata.
    """

    pass
