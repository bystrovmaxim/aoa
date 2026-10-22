# The adversarial breaks (T051)

Each rule was broken in turn. The dedicated test must fail while the rule is broken, and
must pass again once it is restored — the second half is what proves the failure came from
the break and not from something else.

| Rule | Broken in | Test | Result |
|---|---|---|---|
| an empty dictionary cannot classify an axis | `entity_specialization_validator.py` | `test_an_axis_cannot_borrow_from_an_empty_dictionary` | caught |
| a bare code is not accepted where a declared value belongs | `enum_entity.py` | `test_a_bare_code_is_refused` | caught |
| a constructed copy is not a declared value | `enum_entity.py` | `test_a_constructed_copy_is_refused` | caught |
| an alternative must name one of the dictionary's values | `entity_specialization_validator.py` | `test_an_extension_must_name_this_dictionary_s_value` | caught |
| identity, not equality, is what makes a value | `entity_specialization_validator.py` | `test_a_copy_of_a_value_is_not_a_value` | caught |
| every value the head borrows has an alternative | `entity_specialization_validator.py` | `test_a_value_with_no_alternative_is_refused` | caught |
| a class pointing at an axis without being named is refused | `entity_specialization_validator.py` | `test_every_build_rule_refuses_its_own_case` | caught |
| a value that disagrees with the loaded row is refused | `specialization_containers.py` | `test_a_mismatched_pair_is_refused` | caught |
| the marker refuses a code list | `specialization_containers.py` | `test_classifier_refuses_a_list_of_codes` | caught |
