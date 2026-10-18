# Corpus baseline — how many declarations the contract refuses today

**Feature**: `specs/010-aspect-declaration-invariants` | **Task**: T002 | **Date**: 2026-10-18

**Base commit**: `90b2cdeb`. **Environment**: Python 3.12.12.

## How the measurement is made

```bash
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/scan_corpus.py
```

The scan parses declarations rather than matching text, so a signature split across several lines is judged
like one written on one line. It reads three carriers:

- `packages/**/*.py` and `examples/**/*.py` — syntax trees of the modules;
- `examples/**/*.ipynb` — the code cells of every notebook, parsed as source;
- `docs/**/*.md` — every ```` ```python ```` block, parsed as source.

A declaration is **non-conforming** when the rules of this feature would refuse it at declaration time:

| Rule | What the scan checks |
| --- | --- |
| `names` | the parameters match the decorator's contract, in order, including the trailing `ctx` exactly when `@context_requires` is applied *below* the declaration so it can be seen |
| `annotations` | every parameter but `self` carries an annotation |
| `return` | the return carries an annotation |
| `positional` | no keyword-only parameters, `*args` or `**kwargs` |

A declaration inside a `with pytest.raises(...)` block is counted as an **asserted refusal**: it is wrong on
purpose, it is the test of the rule, and the migration must leave it wrong. Everything else is **to migrate**.

**Out of scope of the scan**: the types the annotations resolve to. They need the operation's own `Params` and
`Result`, which exist only when the class is assembled, so they are measured by the tests of US2 rather than by
a static pass.

## The measurement

| Tree | Files | Declarations | Conforming | Non-conforming | of them asserted refusals | to migrate |
| --- | --- | --- | --- | --- | --- | --- |
| packages (**/*.py) | 1209 | 343 | 263 | **80** | 19 | 61 |
| examples (**/*.py) | 156 | 163 | 0 | **163** | 0 | 163 |
| examples (**/*.ipynb) | 154 | 158 | 0 | **158** | 0 | 158 |
| docs (**/*.md, ```python blocks) | 86 | 99 | 1 | **98** | 0 | 98 |
| **total** | | **763** | **264** | **499** | **19** | **480** |

| Declaration | Total | Non-conforming |
| --- | --- | --- |
| `@summary_aspect` | 516 | 331 |
| `@regular_aspect` | 181 | 126 |
| `@on_error` | 28 | 15 |
| `@compensate` | 38 | 27 |

| Fault | Declarations |
| --- | --- |
| names | 27 |
| annotations | 480 |
| return | 441 |
| positional | 0 |

Fault combinations (a declaration can carry several):

| Combination | Declarations |
| --- | --- |
| annotations+return | 436 |
| none | 264 |
| annotations | 36 |
| names | 19 |
| names+annotations+return | 5 |
| names+annotations | 3 |

Notebooks carrying declarations: 76

- `examples/domain_model/01_domain_model.ipynb`
- `examples/extensions/01_opentelemetry.ipynb`
- `examples/how_to/01_custom_adapter.ipynb`
- `examples/how_to/03_custom_plugin.ipynb`
- `examples/how_to/04_custom_logger.ipynb`
- `examples/how_to/05_custom_cache_adapter.ipynb`
- `examples/how_to/07_extend_context.ipynb`
- `examples/how_to/08_custom_intent.ipynb`
- `examples/research_self_knowledge/01_self_audit.ipynb`
- `examples/step_01_Action_and_pipeline/01_hello_world.ipynb`
- `examples/step_01_Action_and_pipeline/02_params_result_and_box.ipynb`
- `examples/step_01_Action_and_pipeline/03_multiple_aspects.ipynb`
- `examples/step_01_Action_and_pipeline/04_inheritance.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/01_checkers.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/02_independent_state.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/03_contract_violation.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/04_contract_preserving_step.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/05_xray_console.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/06_xray_file.ipynb`
- `examples/step_02_state_as_x-ray_of_the_operation/07_opaque.ipynb`
- `examples/step_03_authorization_and_roles/01_roles.ipynb`
- `examples/step_03_authorization_and_roles/02_grant.ipynb`
- `examples/step_03_authorization_and_roles/03_guard.ipynb`
- `examples/step_03_authorization_and_roles/04_access_decide.ipynb`
- `examples/step_03_authorization_and_roles/05_machine_check.ipynb`
- `examples/step_03_authorization_and_roles/06_the_declaration.ipynb`
- `examples/step_03_authorization_and_roles/07_three_answers.ipynb`
- `examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.ipynb`
- `examples/step_03_authorization_and_roles/09_reasons.ipynb`
- `examples/step_03_authorization_and_roles/10_context_in_the_check.ipynb`
- `examples/step_03_authorization_and_roles/11_events.ipynb`
- `examples/step_03_authorization_and_roles/13_cascade.ipynb`
- `examples/step_03_authorization_and_roles/14_guest_and_any.ipynb`
- `examples/step_03_authorization_and_roles/15_alternative_roles.ipynb`
- `examples/step_03_authorization_and_roles/16_silenced_role.ipynb`
- `examples/step_03_authorization_and_roles/17_grant_fallback.ipynb`
- `examples/step_03_authorization_and_roles/21_failure_event.ipynb`
- `examples/step_03_authorization_and_roles/23_invalid_answer.ipynb`
- `examples/step_04_saga_and_compensations/01_saga_compensate.ipynb`
- `examples/step_05_error_handling/01_on_error.ipynb`
- `examples/step_06_dependencies/01_depends.ipynb`
- `examples/step_07_context/01_context.ipynb`
- `examples/step_07_context/02_env.ipynb`
- `examples/step_08_cache/01_cache.ipynb`
- `examples/step_09_plugins/01_ocel.ipynb`
- `examples/step_10_logs/01_logging_sensitive.ipynb`
- `examples/step_13_fastapi/01_service.ipynb`
- `examples/step_13_fastapi/02_auth_override.ipynb`
- `examples/step_13_fastapi/03_login_action.ipynb`
- `examples/step_13_fastapi/04_bearer_auth.ipynb`
- `examples/step_13_fastapi/05_cookie_auth.ipynb`
- `examples/step_13_fastapi/06_jwks_auth.ipynb`
- `examples/step_14_langgraph/01_external_connection.ipynb`
- `examples/step_14_langgraph/01_langgraph.ipynb`
- `examples/step_14_langgraph/02_inline_graph.ipynb`
- `examples/step_14_langgraph/03_function_node.ipynb`
- `examples/step_14_langgraph/04_field_mapping.ipynb`
- `examples/step_14_langgraph/05_testing.ipynb`
- `examples/step_14_langgraph/06_field_mapping.ipynb`
- `examples/step_14_mcp/01_tool.ipynb`
- `examples/step_14_mcp/02_bearer_auth_limitation.ipynb`
- `examples/step_16_complex_input/01_complex_input.ipynb`
- `examples/step_17_connections/01_connections.ipynb`
- `examples/step_17_connections/02_per_call.ipynb`
- `examples/step_17_connections/14_fastapi_lifespan.ipynb`
- `examples/step_17_connections/15_mcp_call.ipynb`
- `examples/step_17_connections/16_pool_lifespan.ipynb`
- `examples/step_18_converters/01_versions.ipynb`
- `examples/step_19_resource/01_resource.ipynb`
- `examples/step_19_resource/02_refusal.ipynb`
- `examples/step_19_resource/03_substitution.ipynb`
- `examples/step_19_resource/07_nested_action.ipynb`
- `examples/step_23_testbench/01_testbench.ipynb`
- `examples/step_24_substitution/01_substitution.ipynb`
- `examples/step_25_context/01_context.ipynb`
- `examples/step_26_maxitor/01_graph.ipynb`

Documentation pages carrying declarations: 26

- `docs/explanation/system-altitudes.md`
- `docs/explanation/verification-must-be-independent.md`
- `docs/explanation/verification-must-be-independent_draft.md`
- `docs/extensions/langgraph.md`
- `docs/extensions/ocel.md`
- `docs/how-to/authoring-action.md`
- `docs/how-to/authoring-adapter.md`
- `docs/how-to/authoring-adapter.ru_draft.md`
- `docs/how-to/authoring-context-extension.md`
- `docs/how-to/migrating-legacy.md`
- `docs/reference/intents-and-invariants.md`
- `docs/reference/intents-and-invariants.ru_draft.md`
- `docs/research/environment-context-port.md`
- `docs/tutorials/step-01-action-and-pipeline.md`
- `docs/tutorials/step-02-state-as-x-ray.md`
- `docs/tutorials/step-03-authorization-and-roles.md`
- `docs/tutorials/step-03-authorization-and-roles.ru_draft.md`
- `docs/tutorials/step-04-saga-and-compensations.md`
- `docs/tutorials/step-05-error-handling.md`
- `docs/tutorials/step-06-dependencies.md`
- `docs/tutorials/step-07-context.md`
- `docs/tutorials/step-09-plugins.md`
- `docs/tutorials/step-17-connections.md`
- `docs/tutorials/step-17-connections.ru_draft.md`
- `docs/tutorials/step-19-resource.md`
- `docs/tutorials/step-19-resource.ru_draft.md`

Files to migrate

### packages (**/*.py) (22 files)

- `packages/aoa-action-machine/examples/02_business_events.py` — 6 fault(s)
- `packages/aoa-action-machine/examples/03_opentelemetry_xray.py` — 6 fault(s)
- `packages/aoa-action-machine/examples/04_fastapi_api.py` — 6 fault(s)
- `packages/aoa-action-machine/examples/05_mcp_tool.py` — 6 fault(s)
- `packages/aoa-action-machine/examples/06_saga_rollback.py` — 10 fault(s)
- `packages/aoa-action-machine/tests/action_machine/graph/nodes/test_action_graph_node.py` — 6 fault(s)
- `packages/aoa-action-machine/tests/action_machine/graph_host/test_graph_execution_adapters.py` — 2 fault(s)
- `packages/aoa-action-machine/tests/action_machine/intents/aspects/test_aspect_decorator_naming.py` — 4 fault(s)
- `packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_check_roles_class_roles.py` — 4 fault(s)
- `packages/aoa-action-machine/tests/action_machine/intents/compensate/test_compensate_decorator.py` — 6 fault(s)
- `packages/aoa-action-machine/tests/action_machine/intents/on_error/test_on_error_decorator.py` — 8 fault(s)
- `packages/aoa-action-machine/tests/action_machine/intents/on_error/test_on_error_method_naming.py` — 2 fault(s)
- `packages/aoa-action-machine/tests/action_machine/runtime/_machine_nested_actions.py` — 12 fault(s)
- `packages/aoa-action-machine/tests/action_machine/runtime/test_error_handler_executor.py` — 1 fault(s)
- `packages/aoa-action-machine/tests/action_machine/scenarios/intents_with_runtime/test_bench_run_compensator.py` — 6 fault(s)
- `packages/aoa-action-machine/tests/support/domain_model/child_action.py` — 1 fault(s)
- `packages/aoa-demo/src/aoa/demo/model/store/actions/ping.py` — 1 fault(s)
- `packages/aoa-langgraph/tests/test_adapter.py` — 8 fault(s)
- `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/left_sidebar_action.py` — 5 fault(s)
- `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/full_graph_action.py` — 1 fault(s)
- `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_domains_action.py` — 1 fault(s)
- `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_node_types_action.py` — 1 fault(s)
### examples (**/*.py) (78 files)

- `examples/domain_model/01_domain_model.py` — 8 fault(s)
- `examples/extensions/01_opentelemetry.py` — 4 fault(s)
- `examples/extensions/02_langgraph.py` — 4 fault(s)
- `examples/how_to/01_custom_adapter.py` — 2 fault(s)
- `examples/how_to/03_custom_plugin.py` — 2 fault(s)
- `examples/how_to/04_custom_logger.py` — 2 fault(s)
- `examples/how_to/05_custom_cache_adapter.py` — 2 fault(s)
- `examples/how_to/07_extend_context.py` — 2 fault(s)
- `examples/how_to/08_custom_intent.py` — 4 fault(s)
- `examples/research_self_knowledge/01_self_audit.py` — 10 fault(s)
- `examples/step_01_Action_and_pipeline/01_hello_world.py` — 2 fault(s)
- `examples/step_01_Action_and_pipeline/02_params_result_and_box.py` — 2 fault(s)
- `examples/step_01_Action_and_pipeline/03_multiple_aspects.py` — 6 fault(s)
- `examples/step_01_Action_and_pipeline/04_inheritance.py` — 10 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/01_checkers.py` — 4 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/02_independent_state.py` — 6 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/03_contract_violation.py` — 4 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/04_contract_preserving_step.py` — 10 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/05_xray_console.py` — 6 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/06_xray_file.py` — 6 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/07_opaque.py` — 4 fault(s)
- `examples/step_03_authorization_and_roles/01_roles.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/02_grant.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/03_guard.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/04_access_decide.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/05_machine_check.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/06_the_declaration.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/07_three_answers.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/09_reasons.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/10_context_in_the_check.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/11_events.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/13_cascade.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/14_guest_and_any.py` — 4 fault(s)
- `examples/step_03_authorization_and_roles/15_alternative_roles.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/16_silenced_role.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/17_grant_fallback.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/21_failure_event.py` — 2 fault(s)
- `examples/step_03_authorization_and_roles/23_invalid_answer.py` — 2 fault(s)
- `examples/step_04_saga_and_compensations/01_saga_compensate.py` — 10 fault(s)
- `examples/step_05_error_handling/01_on_error.py` — 4 fault(s)
- `examples/step_06_dependencies/01_depends.py` — 8 fault(s)
- `examples/step_07_context/01_context.py` — 4 fault(s)
- `examples/step_07_context/02_env.py` — 4 fault(s)
- `examples/step_08_cache/01_cache.py` — 2 fault(s)
- `examples/step_09_plugins/01_ocel.py` — 4 fault(s)
- `examples/step_10_logs/01_logging_sensitive.py` — 2 fault(s)
- `examples/step_13_fastapi/01_service.py` — 4 fault(s)
- `examples/step_13_fastapi/02_auth_override.py` — 1 fault(s)
- `examples/step_13_fastapi/03_login_action.py` — 2 fault(s)
- `examples/step_13_fastapi/04_bearer_auth.py` — 3 fault(s)
- `examples/step_13_fastapi/05_cookie_auth.py` — 3 fault(s)
- `examples/step_13_fastapi/06_jwks_auth.py` — 3 fault(s)
- `examples/step_14_langgraph/01_external_connection.py` — 8 fault(s)
- `examples/step_14_langgraph/01_langgraph.py` — 6 fault(s)
- `examples/step_14_langgraph/02_inline_graph.py` — 8 fault(s)
- `examples/step_14_langgraph/03_function_node.py` — 8 fault(s)
- `examples/step_14_langgraph/04_field_mapping.py` — 8 fault(s)
- `examples/step_14_langgraph/05_testing.py` — 10 fault(s)
- `examples/step_14_langgraph/06_field_mapping.py` — 10 fault(s)
- `examples/step_14_langgraph/07_type_validation.py` — 6 fault(s)
- `examples/step_14_mcp/01_tool.py` — 4 fault(s)
- `examples/step_14_mcp/02_bearer_auth_limitation.py` — 2 fault(s)
- `examples/step_16_complex_input/01_complex_input.py` — 2 fault(s)
- `examples/step_17_connections/01_connections.py` — 2 fault(s)
- `examples/step_17_connections/02_per_call.py` — 2 fault(s)
- `examples/step_17_connections/14_fastapi_lifespan.py` — 2 fault(s)
- `examples/step_17_connections/15_mcp_call.py` — 2 fault(s)
- `examples/step_17_connections/16_pool_lifespan.py` — 2 fault(s)
- `examples/step_18_converters/01_versions.py` — 2 fault(s)
- `examples/step_19_resource/01_resource.py` — 2 fault(s)
- `examples/step_19_resource/02_refusal.py` — 2 fault(s)
- `examples/step_19_resource/03_substitution.py` — 2 fault(s)
- `examples/step_19_resource/07_nested_action.py` — 6 fault(s)
- `examples/step_23_testbench/01_testbench.py` — 8 fault(s)
- `examples/step_24_substitution/01_substitution.py` — 8 fault(s)
- `examples/step_25_context/01_context.py` — 4 fault(s)
- `examples/step_26_maxitor/01_graph.py` — 4 fault(s)
### examples (**/*.ipynb) (76 files)

- `examples/domain_model/01_domain_model.ipynb` — 8 fault(s)
- `examples/extensions/01_opentelemetry.ipynb` — 4 fault(s)
- `examples/how_to/01_custom_adapter.ipynb` — 2 fault(s)
- `examples/how_to/03_custom_plugin.ipynb` — 2 fault(s)
- `examples/how_to/04_custom_logger.ipynb` — 2 fault(s)
- `examples/how_to/05_custom_cache_adapter.ipynb` — 2 fault(s)
- `examples/how_to/07_extend_context.ipynb` — 2 fault(s)
- `examples/how_to/08_custom_intent.ipynb` — 4 fault(s)
- `examples/research_self_knowledge/01_self_audit.ipynb` — 10 fault(s)
- `examples/step_01_Action_and_pipeline/01_hello_world.ipynb` — 2 fault(s)
- `examples/step_01_Action_and_pipeline/02_params_result_and_box.ipynb` — 2 fault(s)
- `examples/step_01_Action_and_pipeline/03_multiple_aspects.ipynb` — 6 fault(s)
- `examples/step_01_Action_and_pipeline/04_inheritance.ipynb` — 10 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/01_checkers.ipynb` — 4 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/02_independent_state.ipynb` — 6 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/03_contract_violation.ipynb` — 4 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/04_contract_preserving_step.ipynb` — 10 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/05_xray_console.ipynb` — 6 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/06_xray_file.ipynb` — 6 fault(s)
- `examples/step_02_state_as_x-ray_of_the_operation/07_opaque.ipynb` — 4 fault(s)
- `examples/step_03_authorization_and_roles/01_roles.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/02_grant.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/03_guard.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/04_access_decide.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/05_machine_check.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/06_the_declaration.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/07_three_answers.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/09_reasons.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/10_context_in_the_check.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/11_events.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/13_cascade.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/14_guest_and_any.ipynb` — 4 fault(s)
- `examples/step_03_authorization_and_roles/15_alternative_roles.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/16_silenced_role.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/17_grant_fallback.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/21_failure_event.ipynb` — 2 fault(s)
- `examples/step_03_authorization_and_roles/23_invalid_answer.ipynb` — 2 fault(s)
- `examples/step_04_saga_and_compensations/01_saga_compensate.ipynb` — 10 fault(s)
- `examples/step_05_error_handling/01_on_error.ipynb` — 4 fault(s)
- `examples/step_06_dependencies/01_depends.ipynb` — 8 fault(s)
- `examples/step_07_context/01_context.ipynb` — 4 fault(s)
- `examples/step_07_context/02_env.ipynb` — 4 fault(s)
- `examples/step_08_cache/01_cache.ipynb` — 2 fault(s)
- `examples/step_09_plugins/01_ocel.ipynb` — 4 fault(s)
- `examples/step_10_logs/01_logging_sensitive.ipynb` — 2 fault(s)
- `examples/step_13_fastapi/01_service.ipynb` — 4 fault(s)
- `examples/step_13_fastapi/02_auth_override.ipynb` — 1 fault(s)
- `examples/step_13_fastapi/03_login_action.ipynb` — 2 fault(s)
- `examples/step_13_fastapi/04_bearer_auth.ipynb` — 3 fault(s)
- `examples/step_13_fastapi/05_cookie_auth.ipynb` — 3 fault(s)
- `examples/step_13_fastapi/06_jwks_auth.ipynb` — 3 fault(s)
- `examples/step_14_langgraph/01_external_connection.ipynb` — 8 fault(s)
- `examples/step_14_langgraph/01_langgraph.ipynb` — 6 fault(s)
- `examples/step_14_langgraph/02_inline_graph.ipynb` — 8 fault(s)
- `examples/step_14_langgraph/03_function_node.ipynb` — 8 fault(s)
- `examples/step_14_langgraph/04_field_mapping.ipynb` — 8 fault(s)
- `examples/step_14_langgraph/05_testing.ipynb` — 10 fault(s)
- `examples/step_14_langgraph/06_field_mapping.ipynb` — 10 fault(s)
- `examples/step_14_mcp/01_tool.ipynb` — 4 fault(s)
- `examples/step_14_mcp/02_bearer_auth_limitation.ipynb` — 2 fault(s)
- `examples/step_16_complex_input/01_complex_input.ipynb` — 2 fault(s)
- `examples/step_17_connections/01_connections.ipynb` — 2 fault(s)
- `examples/step_17_connections/02_per_call.ipynb` — 2 fault(s)
- `examples/step_17_connections/14_fastapi_lifespan.ipynb` — 2 fault(s)
- `examples/step_17_connections/15_mcp_call.ipynb` — 2 fault(s)
- `examples/step_17_connections/16_pool_lifespan.ipynb` — 2 fault(s)
- `examples/step_18_converters/01_versions.ipynb` — 2 fault(s)
- `examples/step_19_resource/01_resource.ipynb` — 2 fault(s)
- `examples/step_19_resource/02_refusal.ipynb` — 2 fault(s)
- `examples/step_19_resource/03_substitution.ipynb` — 2 fault(s)
- `examples/step_19_resource/07_nested_action.ipynb` — 6 fault(s)
- `examples/step_23_testbench/01_testbench.ipynb` — 8 fault(s)
- `examples/step_24_substitution/01_substitution.ipynb` — 8 fault(s)
- `examples/step_25_context/01_context.ipynb` — 4 fault(s)
- `examples/step_26_maxitor/01_graph.ipynb` — 4 fault(s)
### docs (**/*.md, ```python blocks) (26 files)

- `docs/explanation/system-altitudes.md` — 2 fault(s)
- `docs/explanation/verification-must-be-independent.md` — 4 fault(s)
- `docs/explanation/verification-must-be-independent_draft.md` — 4 fault(s)
- `docs/extensions/langgraph.md` — 2 fault(s)
- `docs/extensions/ocel.md` — 2 fault(s)
- `docs/how-to/authoring-action.md` — 8 fault(s)
- `docs/how-to/authoring-adapter.md` — 2 fault(s)
- `docs/how-to/authoring-adapter.ru_draft.md` — 2 fault(s)
- `docs/how-to/authoring-context-extension.md` — 2 fault(s)
- `docs/how-to/migrating-legacy.md` — 12 fault(s)
- `docs/reference/intents-and-invariants.md` — 4 fault(s)
- `docs/reference/intents-and-invariants.ru_draft.md` — 4 fault(s)
- `docs/research/environment-context-port.md` — 5 fault(s)
- `docs/tutorials/step-01-action-and-pipeline.md` — 10 fault(s)
- `docs/tutorials/step-02-state-as-x-ray.md` — 18 fault(s)
- `docs/tutorials/step-03-authorization-and-roles.md` — 38 fault(s)
- `docs/tutorials/step-03-authorization-and-roles.ru_draft.md` — 38 fault(s)
- `docs/tutorials/step-04-saga-and-compensations.md` — 6 fault(s)
- `docs/tutorials/step-05-error-handling.md` — 8 fault(s)
- `docs/tutorials/step-06-dependencies.md` — 4 fault(s)
- `docs/tutorials/step-07-context.md` — 4 fault(s)
- `docs/tutorials/step-09-plugins.md` — 2 fault(s)
- `docs/tutorials/step-17-connections.md` — 2 fault(s)
- `docs/tutorials/step-17-connections.ru_draft.md` — 2 fault(s)
- `docs/tutorials/step-19-resource.md` — 2 fault(s)
- `docs/tutorials/step-19-resource.ru_draft.md` — 2 fault(s)
```


## What the numbers say

1. **The rules would refuse 499 of 763 declarations today.** The bulk is not misnaming — it is the absence of
   annotations: 480 declarations have an unannotated parameter, 441 have no return annotation, and 436 have
   both. Only 27 have a name or order fault, and 5 of those are deliberate.
2. **The `.py` corpus under `examples/` is entirely non-conforming** (163 of 163), and so are the notebooks
   (158 of 158): every example predates the rule. That is the largest part of the migration and it is
   mechanical — the parameters are the same four names everywhere.
3. **`packages/` is in better shape than the earlier estimate said**: 80 non-conforming, not 104. The
   difference is exactly 24 declarations, measured by re-running the earlier judgement over the same tree: all
   24 are `@on_error` or `@compensate` methods that match *their own* contract
   (`self, params, state, box, connections, error` and `self, params, state_before, state_after, box,
   connections, error`), and the earlier pass compared every declaration against the summary's name list, so it
   counted each of them as misnamed. The scan now judges each decorator against its own contract.
4. **19 declarations are deliberately wrong.** They sit inside `pytest.raises` blocks in
   `test_aspect_decorator_naming.py`, `test_compensate_decorator.py` and `test_on_error_method_naming.py`, and
   they are the tests that prove the refusals fire. They must stay wrong; what changes is the message they
   expect.
5. **The documentation is nearly all non-conforming too** (98 of 99 snippets in 26 pages). A reader who copies
   a page would write a declaration the framework now refuses — which is why the documentation is part of this
   change and not a follow-up.

## Consequence for the specification and the task list

The figures the specification first carried — 523 non-conforming, 211 of them in `.py` — came from an earlier
pass that judged only two of the four decorators and compared every declaration against the summary's name
list. The measured figures are **499 non-conforming, 480 to migrate, 19 deliberate**. The specification, the
plan, the research note and the task list are corrected to these numbers in the same pass as this file, and
`SC-003` is restated as "zero unintentional sites, and the 19 deliberate ones each named with the test that
asserts its refusal", because a literal zero is unreachable while the tests of the rule exist.

## Reproducing

The scan is deterministic and takes about a second:

```bash
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/scan_corpus.py            # the report below
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/scan_corpus.py --json     # raw records
.venv/bin/python specs/010-aspect-declaration-invariants/evidence/scan_corpus.py --root ..  # another checkout
```

After the migration (T036, T039) the same command must report the same 763 declarations, 264 conforming, 19
deliberate refusals and **0 to migrate**.

## The scan's output, verbatim

```text
