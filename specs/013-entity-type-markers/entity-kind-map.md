# Entity kind map — the 476 decisions, for review

**Feature**: `specs/013-entity-type-markers` | **Date**: 2026-10-22

Generated from `evidence/entity_kind_map.py`. Totals: **core** 290, **spec** 148, **assoc** 19, **detail** 16; **14** rows marked _review_.

The kind is chosen by what an instance represents, not by the shape of a table. A row marked _review_ rests on a name or module pattern rather than on structure — confirm or correct those before the codemod runs.

## Rows that need your decision

| Class | Module | Kind | New name | Why it is uncertain |
| --- | --- | --- | --- | --- |
| `OrderLineEntity` | `examples/domain_model/01_domain_model.py` | detail | `OrderLineDetailEntity` | is named as a part of its owner |
| `OrderLineEntity` | `examples/step_21_relations/01_relations.py` | detail | `OrderLineDetailEntity` | is named as a part of its owner |
| `AnalyticsCanonicalTelemetryRowEntity` | `analytics/entities/analytics_canonical_telemetry_row.py` | detail | `AnalyticsCanonicalTelemetryRowDetailEntity` | is named as a part of its owner |
| `AnalyticsDedupBloomRowEntity` | `analytics/entities/analytics_dedup_bloom_row.py` | detail | `AnalyticsDedupBloomRowDetailEntity` | is named as a part of its owner |
| `AssuranceRegulatedExpectationRowEntity` | `assurance_portfolio/entities/ap_regulated_expectation_row.py` | detail | `AssuranceRegulatedExpectationRowDetailEntity` | is named as a part of its owner |
| `AssuranceScenarioInstructionLineEntity` | `assurance_portfolio/entities/ap_scenario_instruction_line.py` | detail | `AssuranceScenarioInstructionLineDetailEntity` | is named as a part of its owner |
| `ClinicalOutboundParcelLineEntity` | `clinical_supply/entities/cs_outbound_parcel_line.py` | detail | `ClinicalOutboundParcelLineDetailEntity` | is named as a part of its owner |
| `StorageAisleRowEntity` | `inventory/entities/inv_storage_aisle_row.py` | detail | `StorageAisleRowDetailEntity` | is named as a part of its owner |
| `FacilityHandoffManifestEntity` | `logistics_mesh/entities/facility_handoff_manifest_entity.py` | assoc | `FacilityHandoffManifestAssocEntity` | is named as a technical connection (module) and carries no lifecycle |
| `AuditLogEntryEntity` | `store/entities/audit_log_entry.py` | detail | `AuditLogEntryDetailEntity` | is named as a part of its owner |
| `SalesOrderLineEntity` | `store/entities/sales_core.py` | detail | `SalesOrderLineDetailEntity` | is named as a part of its owner |
| `KitExplosionLineEntity` | `store/entities/store_line_kit_explosion.py` | detail | `KitExplosionLineDetailEntity` | is named as a part of its owner |
| `LineShipmentPieceEntity` | `store/entities/store_line_shipment_piece.py` | detail | `LineShipmentPieceDetailEntity` | is named as a part of its owner |
| `TaxLineEntity` | `store/entities/tax_line.py` | detail | `TaxLineDetailEntity` | is named as a part of its owner |

## The full table, grouped by module

### `examples/domain_model/01_domain_model.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CustomerEntity` | core | `CustomerCoreEntity` | carries its own identity, lifecycle or business fields |
| `OrderEntity` | core | `OrderCoreEntity` | declares Composite parts, so it owns them: an aggregate root |
| `OrderLineEntity` | detail _(review)_ | `OrderLineDetailEntity` | is named as a part of its owner |

### `examples/step_09_plugins/01_ocel.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderEntity` | core | `OrderCoreEntity` | declares Composite parts, so it owns them: an aggregate root |

### `examples/step_15_schema_results/01_schema_results.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_20_entity/01_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/01_relations.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CustomerEntity` | core | `CustomerCoreEntity` | carries its own identity, lifecycle or business fields |
| `OrderEntity` | core | `OrderCoreEntity` | declares Composite parts, so it owns them: an aggregate root |
| `OrderLineEntity` | detail _(review)_ | `OrderLineDetailEntity` | is named as a part of its owner |

### `examples/step_21_relations/02_specialization.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/03_specialization_unloaded.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/04_specialization_reverse.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/05_specialization_mapping.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/06_specialization_wrong_type.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/07_specialization_data_codes.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/08_specialization_mismatched_data.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/09_specialization_frozen.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/10_specialization_graph.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/11_specialization_two_axes.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/12_specialization_hidden_edges.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/13_specialization_erd.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/14_specialization_single_alternative.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/20_error_missing_classifier.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/21_error_missing_code.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/22_error_multiple_codes.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/23_error_unknown_head_code.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/24_error_extra_alternative_code.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/25_error_duplicate_code.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/26_error_classifier_type.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/27_error_classifier_missing_field.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/28_error_classifier_self.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/29_error_inverse_name.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/30_error_no_reverse.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | core | `FirstPressCoreEntity` | carries its own identity, lifecycle or business fields |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/31_error_two_reverse_fields.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/32_error_undeclared_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/33_error_shared_classifier.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/34_error_two_heads.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `OtherRecordEntity` | core | `OtherRecordCoreEntity` | carries its own identity, lifecycle or business fields |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/35_error_outside_alternative.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `UnlistedPressEntity` | spec | `UnlistedPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/36_error_relation_classifier.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/37_error_cycle.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AEntity` | spec | `ASpecEntity` | declares a Generalization, so it is variant data of its head |
| `BEntity` | spec | `BSpecEntity` | declares a Generalization, so it is variant data of its head |

### `examples/step_21_relations/38_error_axis_subset.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_21_relations/39_error_machine_build.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FirstPressEntity` | spec | `FirstPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RepressEntity` | spec | `RepressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TestPressEntity` | spec | `TestPressSpecEntity` | declares a Generalization, so it is variant data of its head |
| `VinylRecordEntity` | core | `VinylRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_22_lifecycle/01_lifecycle.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_22_lifecycle/05_graph_attributes.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_22_lifecycle/06_maxitor_states.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_22_lifecycle/19_non_json_field.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `examples/step_26_maxitor/01_graph.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CustomerEntity` | core | `CustomerCoreEntity` | carries its own identity, lifecycle or business fields |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/domain/test_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ValidEntity` | core | `ValidCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/domain/test_entity_introspection.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ChildEntity` | assoc | `ChildAssocEntity` | carries only participant references and service fields |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/domain/test_hydration.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DummyEntity` | core | `DummyCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/domain/test_testing.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `_FloatDefaultEntity` | core | `_FloatDefaultCoreEntity` | carries its own identity, lifecycle or business fields |
| `_LifecycleGetterEntity` | core | `_LifecycleGetterCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/graph/test_entity_schema_graph_edge.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrphanWireEntity` | core | `OrphanWireCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_graph.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `_FirstEntity` | spec | `_FirstSpecEntity` | declares a Generalization, so it is variant data of its head |
| `_HeadEntity` | core | `_HeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `_PlainEntity` | core | `_PlainCoreEntity` | carries its own identity, lifecycle or business fields |
| `_SecondEntity` | spec | `_SecondSpecEntity` | declares a Generalization, so it is variant data of its head |
| `_ThirdEntity` | spec | `_ThirdSpecEntity` | declares a Generalization, so it is variant data of its head |

### `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_axis.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ExtraCodeAlternativeEntity` | spec | `ExtraCodeAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `ExtraCodeHeadEntity` | core | `ExtraCodeHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `GoodAlternativeEntity` | spec | `GoodAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `GoodHeadEntity` | core | `GoodHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `IntegerAlternativeEntity` | spec | `IntegerAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `IntegerHeadEntity` | core | `IntegerHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `MismatchedAlternativeEntity` | spec | `MismatchedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `MismatchedHeadEntity` | core | `MismatchedHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `MissingClassifierAlternativeEntity` | spec | `MissingClassifierAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `MissingClassifierHeadEntity` | assoc | `MissingClassifierHeadAssocEntity` | carries only participant references and service fields |
| `RelationClassifiedAlternativeEntity` | spec | `RelationClassifiedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RelationClassifiedHeadEntity` | assoc | `RelationClassifiedHeadAssocEntity` | carries only participant references and service fields |
| `RelationClassifiedOtherEntity` | assoc | `RelationClassifiedOtherAssocEntity` | carries only participant references and service fields |
| `SelfClassifiedAlternativeEntity` | spec | `SelfClassifiedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SelfClassifiedHeadEntity` | assoc | `SelfClassifiedHeadAssocEntity` | carries only participant references and service fields |
| `SilentAlternativeEntity` | spec | `SilentAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SilentHeadEntity` | core | `SilentHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `StrangerAxisEntity` | assoc | `StrangerAxisAssocEntity` | carries only participant references and service fields |
| `StrangerHeadEntity` | core | `StrangerHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `TwoWayAlternativeEntity` | spec | `TwoWayAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TwoWayHeadEntity` | core | `TwoWayHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `UnreachableAlternativeEntity` | assoc | `UnreachableAlternativeAssocEntity` | carries only participant references and service fields |
| `UnreachableHeadEntity` | core | `UnreachableHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `WronglyPairedAlternativeEntity` | spec | `WronglyPairedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `WronglyPairedHeadEntity` | core | `WronglyPairedHeadCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_rules_global.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClosedHeadEntity` | core | `ClosedHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `CycleAEntity` | spec | `CycleASpecEntity` | declares a Generalization, so it is variant data of its head |
| `CycleBEntity` | spec | `CycleBSpecEntity` | declares a Generalization, so it is variant data of its head |
| `FirstClaimHeadEntity` | core | `FirstClaimHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `FirstSharedClassifierAlternativeEntity` | spec | `FirstSharedClassifierAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `IntruderEntity` | spec | `IntruderSpecEntity` | declares a Generalization, so it is variant data of its head |
| `NamedAlternativeEntity` | spec | `NamedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SecondClaimHeadEntity` | core | `SecondClaimHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `SecondSharedClassifierAlternativeEntity` | spec | `SecondSharedClassifierAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SelfCycleEntity` | spec | `SelfCycleSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SharedClassEntity` | spec | `SharedClassSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SharedClassifierHeadEntity` | core | `SharedClassifierHeadCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-action-machine/tests/action_machine/graph/test_entity_specialization_sweep.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClaimFirstHeadEntity` | core | `ClaimFirstHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `ClaimSecondHeadEntity` | core | `ClaimSecondHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `ClaimedTwiceEntity` | spec | `ClaimedTwiceSpecEntity` | declares a Generalization, so it is variant data of its head |
| `ClosedIntruderEntity` | spec | `ClosedIntruderSpecEntity` | declares a Generalization, so it is variant data of its head |
| `ClosedNamedEntity` | spec | `ClosedNamedSpecEntity` | declares a Generalization, so it is variant data of its head |
| `ClosedSweepHeadEntity` | core | `ClosedSweepHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `CodeLessAlternativeEntity` | spec | `CodeLessAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `GoodFirstEntity` | spec | `GoodFirstSpecEntity` | declares a Generalization, so it is variant data of its head |
| `GoodHeadEntity` | core | `GoodHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `GoodSecondEntity` | spec | `GoodSecondSpecEntity` | declares a Generalization, so it is variant data of its head |
| `HeadOverCodeLessEntity` | core | `HeadOverCodeLessCoreEntity` | carries its own identity, lifecycle or business fields |
| `HeadOverOrphanCodeEntity` | core | `HeadOverOrphanCodeCoreEntity` | carries its own identity, lifecycle or business fields |
| `HeadOverUndeclaredEntity` | core | `HeadOverUndeclaredCoreEntity` | carries its own identity, lifecycle or business fields |
| `MismatchedTwinEntity` | spec | `MismatchedTwinSpecEntity` | declares a Generalization, so it is variant data of its head |
| `MissingClassifierAlternativeEntity` | spec | `MissingClassifierAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `MissingClassifierHeadEntity` | assoc | `MissingClassifierHeadAssocEntity` | carries only participant references and service fields |
| `NotAnEntityAlternativeEntity` | assoc | `NotAnEntityAlternativeAssocEntity` | carries only participant references and service fields |
| `NumericClassifiedAlternativeEntity` | spec | `NumericClassifiedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `NumericClassifiedHeadEntity` | core | `NumericClassifiedHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `OrphanCodeAlternativeEntity` | spec | `OrphanCodeAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RelationClassifiedAlternativeEntity` | spec | `RelationClassifiedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `RelationClassifiedHeadEntity` | assoc | `RelationClassifiedHeadAssocEntity` | carries only participant references and service fields |
| `RelationOtherEntity` | assoc | `RelationOtherAssocEntity` | carries only participant references and service fields |
| `SelfClassifiedAlternativeEntity` | spec | `SelfClassifiedAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SelfClassifiedHeadEntity` | assoc | `SelfClassifiedHeadAssocEntity` | carries only participant references and service fields |
| `SelfReferringHeadEntity` | spec | `SelfReferringHeadSpecEntity` | declares a Generalization, so it is variant data of its head |
| `ShortFirstEntity` | spec | `ShortFirstSpecEntity` | declares a Generalization, so it is variant data of its head |
| `ShortHeadEntity` | core | `ShortHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `ShortSecondEntity` | spec | `ShortSecondSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TwoAxisFirstEntity` | spec | `TwoAxisFirstSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TwoAxisHeadEntity` | core | `TwoAxisHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `TwoAxisSecondEntity` | spec | `TwoAxisSecondSpecEntity` | declares a Generalization, so it is variant data of its head |
| `TwoFaultsHeadEntity` | core | `TwoFaultsHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `TwoFaultsNumericHeadEntity` | core | `TwoFaultsNumericHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `TwoFaultsTextHeadEntity` | core | `TwoFaultsTextHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `UndeclaredAlternativeEntity` | assoc | `UndeclaredAlternativeAssocEntity` | carries only participant references and service fields |
| `UnfittingAlternativeEntity` | spec | `UnfittingAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |
| `UnknownCodeAlternativeEntity` | spec | `UnknownCodeAlternativeSpecEntity` | declares a Generalization, so it is variant data of its head |

### `packages/aoa-action-machine/tests/action_machine/graph/test_graph_json_schema_specialization.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SchemaFirstEntity` | spec | `SchemaFirstSpecEntity` | declares a Generalization, so it is variant data of its head |
| `SchemaHeadEntity` | core | `SchemaHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `SchemaSecondEntity` | spec | `SchemaSecondSpecEntity` | declares a Generalization, so it is variant data of its head |

### `packages/aoa-action-machine/tests/action_machine/intents/entity/test_entity_intent_resolver.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `_HostEntity` | assoc | `_HostAssocEntity` | carries only participant references and service fields |
| `_TargetEntity` | assoc | `_TargetAssocEntity` | carries only participant references and service fields |

### `packages/aoa-action-machine/tests/action_machine/intents/entity/test_entity_specialization_resolver.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `_BareContainerEntity` | assoc | `_BareContainerAssocEntity` | carries only participant references and service fields |
| `_FirstEntity` | spec | `_FirstSpecEntity` | declares a Generalization, so it is variant data of its head |
| `_FirstForSilentEntity` | spec | `_FirstForSilentSpecEntity` | declares a Generalization, so it is variant data of its head |
| `_GreedyEntity` | spec | `_GreedySpecEntity` | declares a Generalization, so it is variant data of its head |
| `_HeadEntity` | core | `_HeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `_HeadWithGreedyEntity` | core | `_HeadWithGreedyCoreEntity` | carries its own identity, lifecycle or business fields |
| `_HeadWithSilentEntity` | core | `_HeadWithSilentCoreEntity` | carries its own identity, lifecycle or business fields |
| `_HeadWithTwinEntity` | core | `_HeadWithTwinCoreEntity` | carries its own identity, lifecycle or business fields |
| `_PlainEntity` | core | `_PlainCoreEntity` | carries its own identity, lifecycle or business fields |
| `_QuietHeadEntity` | core | `_QuietHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `_SecondEntity` | spec | `_SecondSpecEntity` | declares a Generalization, so it is variant data of its head |
| `_SilentEntity` | spec | `_SilentSpecEntity` | declares a Generalization, so it is variant data of its head |
| `_ThirdEntity` | spec | `_ThirdSpecEntity` | declares a Generalization, so it is variant data of its head |
| `_TwinAEntity` | spec | `_TwinASpecEntity` | declares a Generalization, so it is variant data of its head |
| `_TwinBEntity` | spec | `_TwinBSpecEntity` | declares a Generalization, so it is variant data of its head |

### `packages/aoa-action-machine/tests/support/domain_model/entities.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ComplexEntity` | core | `ComplexCoreEntity` | carries its own identity, lifecycle or business fields |
| `LifecycleEntity` | core | `LifecycleCoreEntity` | carries its own identity, lifecycle or business fields |
| `RelatedEntity` | core | `RelatedCoreEntity` | carries its own identity, lifecycle or business fields |
| `SampleEntity` | core | `SampleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/access_cascade/entities/cascade_boundary_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CascadeBoundaryEntity` | assoc | `CascadeBoundaryAssocEntity` | carries only participant references and service fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_aggregate_sketch_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsAggregateSketchStubEntity` | core | `AnalyticsAggregateSketchStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_canonical_telemetry_row.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsCanonicalTelemetryRowEntity` | detail _(review)_ | `AnalyticsCanonicalTelemetryRowDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_dedup_bloom_row.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsDedupBloomRowEntity` | detail _(review)_ | `AnalyticsDedupBloomRowDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_er_cycle_quad_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsDirectedCycleQuadAEntity` | core | `AnalyticsDirectedCycleQuadACoreEntity` | carries its own identity, lifecycle or business fields |
| `AnalyticsDirectedCycleQuadBEntity` | core | `AnalyticsDirectedCycleQuadBCoreEntity` | carries its own identity, lifecycle or business fields |
| `AnalyticsDirectedCycleQuadCEntity` | core | `AnalyticsDirectedCycleQuadCCoreEntity` | carries its own identity, lifecycle or business fields |
| `AnalyticsDirectedCycleQuadDEntity` | core | `AnalyticsDirectedCycleQuadDCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_ingress_batch.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsIngressBatchEntity` | core | `AnalyticsIngressBatchCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_mesh_canonical_sampling.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsCanonicalSamplingCorrelateEntity` | core | `AnalyticsCanonicalSamplingCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_mesh_dedup_dimension.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsDedupDimensionCorrelateEntity` | core | `AnalyticsDedupDimensionCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_mesh_rollup_privacy.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsRollupPrivacyCorrelateEntity` | core | `AnalyticsRollupPrivacyCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_metric_rollup_staging.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsMetricRollupStagingEntity` | core | `AnalyticsMetricRollupStagingCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sampling_policy.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AnalyticsSamplingPolicyEntity` | core | `AnalyticsSamplingPolicyCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_budgeted_query_plan.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BudgetedQueryPlanEntity` | core | `BudgetedQueryPlanCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_data_quality_ticket.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DataQualityTicketEntity` | core | `DataQualityTicketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_derived_metric_fence.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DerivedMetricFenceEntity` | core | `DerivedMetricFenceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_dimension_slice_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DimensionSliceStubEntity` | core | `DimensionSliceStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_experiment_overlay.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ExperimentOverlayEntity` | core | `ExperimentOverlayCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_geo_shard_hint.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `GeoShardHintEntity` | core | `GeoShardHintCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_privacy_budget_slice.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `PrivacyBudgetSliceEntity` | core | `PrivacyBudgetSliceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_replay_watermark_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ReplayWatermarkStubEntity` | core | `ReplayWatermarkStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_time_bucket_mapper.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `TimeBucketMapperEntity` | core | `TimeBucketMapperCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/analytics/entities/analytics_sat_user_hash_salt_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `UserHashSaltStubEntity` | core | `UserHashSaltStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_actor_duty_coupling.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceActorDutyCouplingEntity` | core | `AssuranceActorDutyCouplingCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_campaign_wave_banner.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceCampaignWaveBannerEntity` | core | `AssuranceCampaignWaveBannerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_delegated_work_ticket.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceDelegatedWorkTicketEntity` | core | `AssuranceDelegatedWorkTicketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_duty_privilege_bridge.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceDutyPrivilegeBridgeEntity` | core | `AssuranceDutyPrivilegeBridgeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_evidence_carrier_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceEvidenceCarrierStubEntity` | core | `AssuranceEvidenceCarrierStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_execution_attempt_ticket.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceExecutionAttemptTicketEntity` | core | `AssuranceExecutionAttemptTicketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_expectation_catalog_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceExpectationCatalogStubEntity` | core | `AssuranceExpectationCatalogStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_expectation_outline_node.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceExpectationOutlineNodeEntity` | core | `AssuranceExpectationOutlineNodeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_facility_actor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceFacilityActorEntity` | core | `AssuranceFacilityActorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_instruction_expectation_anchor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceInstructionExpectationAnchorEntity` | core | `AssuranceInstructionExpectationAnchorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_portfolio_lane_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssurancePortfolioLaneStubEntity` | core | `AssurancePortfolioLaneStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_portfolio_workspace_coupler.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssurancePortfolioWorkspaceCouplerEntity` | core | `AssurancePortfolioWorkspaceCouplerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_reference_axes.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceAccountPhaseAxisEntity` | core | `AssuranceAccountPhaseAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssuranceCheckpointToneAxisEntity` | core | `AssuranceCheckpointToneAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssuranceDelegationIntentAxisEntity` | core | `AssuranceDelegationIntentAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssuranceDutyTemplateAxisEntity` | core | `AssuranceDutyTemplateAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssuranceEvidenceKindAxisEntity` | core | `AssuranceEvidenceKindAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssuranceExpectationGenreAxisEntity` | core | `AssuranceExpectationGenreAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssuranceExpectationPhaseAxisEntity` | core | `AssuranceExpectationPhaseAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssurancePrivilegeGrainAxisEntity` | core | `AssurancePrivilegeGrainAxisCoreEntity` | carries its own identity, lifecycle or business fields |
| `AssuranceSpecificationDepthAxisEntity` | core | `AssuranceSpecificationDepthAxisCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_regulated_expectation_row.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceRegulatedExpectationRowEntity` | detail _(review)_ | `AssuranceRegulatedExpectationRowDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_scenario_instruction_line.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceScenarioInstructionLineEntity` | detail _(review)_ | `AssuranceScenarioInstructionLineDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_scenario_sheet.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceScenarioSheetEntity` | core | `AssuranceScenarioSheetCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_wave_execution_slot.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceWaveExecutionSlotEntity` | core | `AssuranceWaveExecutionSlotCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_wave_seat_coupling.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceWaveSeatCouplingEntity` | core | `AssuranceWaveSeatCouplingCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_workspace_program_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceWorkspaceProgramStubEntity` | core | `AssuranceWorkspaceProgramStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_workspace_seat_grant.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AssuranceWorkspaceSeatGrantEntity` | core | `AssuranceWorkspaceSeatGrantCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/arbitration_brief_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ArbitrationBriefStubEntity` | core | `ArbitrationBriefStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_canonical_row_artifact.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BillingCanonicalRowArtifactEntity` | core | `BillingCanonicalRowArtifactCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_file_ingest_manifest.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BillingFileIngestManifestEntity` | core | `BillingFileIngestManifestCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_mesh_chargeback_ingest.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BillingChargebackIngestCorrelateEntity` | core | `BillingChargebackIngestCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_mesh_parse_interchange.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BillingParseInterchangeBridgeEntity` | core | `BillingParseInterchangeBridgeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_multi_lifecycle_table_entities.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IssuerDisputeWorkbenchEntity` | core | `IssuerDisputeWorkbenchCoreEntity` | carries its own identity, lifecycle or business fields |
| `MultiRingSettlementAuditEntity` | core | `MultiRingSettlementAuditCoreEntity` | carries its own identity, lifecycle or business fields |
| `TreasuryCutoverBundleEntity` | core | `TreasuryCutoverBundleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_parse_pass.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BillingParsePassEntity` | core | `BillingParsePassCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_payout_plan.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BillingPayoutPlanEntity` | core | `BillingPayoutPlanCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_acquirer_integrity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AcquirerIntegrityCheckEntity` | core | `AcquirerIntegrityCheckCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_cash_apply_hint.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CashApplicationHintEntity` | core | `CashApplicationHintCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_duplicate_ledger.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DuplicateSuppressionLedgerEntity` | core | `DuplicateSuppressionLedgerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_fee_schedule_ptr.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `MerchantFeeSchedulePointerEntity` | core | `MerchantFeeSchedulePointerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_fx_residual.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FxResidualTagEntity` | core | `FxResidualTagCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_interchange_slice.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `InterchangeAssessmentSliceEntity` | core | `InterchangeAssessmentSliceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_ledger_mirror_offset.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LedgerMirrorOffsetEntity` | core | `LedgerMirrorOffsetCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_narrative_correction.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `NarrativeCorrectionEntity` | core | `NarrativeCorrectionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_profit_center_slice.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ProfitCenterContributionEntity` | core | `ProfitCenterContributionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_regulatory_ptr.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RegulatorySubmissionPointerEntity` | core | `RegulatorySubmissionPointerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_ripple_correction.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SettlementRippleCorrectionEntity` | core | `SettlementRippleCorrectionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_tax_remit_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `TaxRemittanceAdviceEntity` | core | `TaxRemittanceAdviceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sweep_instruction.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BillingSweepInstructionEntity` | core | `BillingSweepInstructionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/chargeback_ticket.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ChargebackTicketEntity` | core | `ChargebackTicketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/funding_window_hint.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FundingWindowHintEntity` | core | `FundingWindowHintCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/payment_event_log.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `PaymentEventLogEntity` | core | `PaymentEventLogCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/billing/entities/retrieval_evidence_bundle.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RetrievalEvidenceBundleEntity` | core | `RetrievalEvidenceBundleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_acquisition_channel_ledger.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AcquisitionChannelLedgerEntity` | core | `AcquisitionChannelLedgerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_audience_segment_glue.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AudienceSegmentGlueEntity` | core | `AudienceSegmentGlueCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_availability_projection.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AvailabilityProjectionEntity` | core | `AvailabilityProjectionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_bridge_price_acquisition.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CatalogPriceAcquisitionLinkEntity` | core | `CatalogPriceAcquisitionLinkCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_bridge_shelf_bundle.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CatalogShelfBundleLinkEntity` | core | `CatalogShelfBundleLinkCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_bundle_cardinality_rule.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BundleCardinalityRuleEntity` | core | `BundleCardinalityRuleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_conversion_attribution_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ConversionAttributionStubEntity` | core | `ConversionAttributionStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_er_cycle_triangle_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CatalogDirectedCycleTriangleAEntity` | core | `CatalogDirectedCycleTriangleACoreEntity` | carries its own identity, lifecycle or business fields |
| `CatalogDirectedCycleTriangleBEntity` | core | `CatalogDirectedCycleTriangleBCoreEntity` | carries its own identity, lifecycle or business fields |
| `CatalogDirectedCycleTriangleCEntity` | core | `CatalogDirectedCycleTriangleCCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_merch_copy_variant.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `MerchCopyVariantEntity` | core | `MerchCopyVariantCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_price_ribbon_snapshot.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `PriceRibbonSnapshotEntity` | core | `PriceRibbonSnapshotCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_regulatory_label_pack.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RegulatoryLabelPackEntity` | core | `RegulatoryLabelPackCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_search_boost_weight.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SearchBoostWeightEntity` | core | `SearchBoostWeightCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_shelf_placement_hint.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ShelfPlacementHintEntity` | core | `ShelfPlacementHintCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_touch_moment.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `TouchMomentEntity` | core | `TouchMomentCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog/entities/product_row.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CatalogProductEntity` | core | `CatalogProductCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog_custody/entities/custody_audit_event_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CustodyAuditEventEntity` | core | `CustodyAuditEventCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/catalog_custody/entities/regulated_stock_keeping_unit_row_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RegulatedStockKeepingUnitRowEntity` | detail | `RegulatedStockKeepingUnitRowDetailEntity` | is named as a part of its owner (module) and carries no lifecycle |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_care_site_unit.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalCareSiteUnitEntity` | core | `ClinicalCareSiteUnitCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_consumable_sku_row.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalConsumableSkuEntity` | core | `ClinicalConsumableSkuCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_geographic_anchor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalGeographicAnchorEntity` | core | `ClinicalGeographicAnchorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_inbound_shipment_ticket.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalInboundShipmentTicketEntity` | core | `ClinicalInboundShipmentTicketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_inbound_transport_binding.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalInboundTransportBindingEntity` | core | `ClinicalInboundTransportBindingCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_material_anchor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalMaterialAnchorEntity` | core | `ClinicalMaterialAnchorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_outbound_parcel_line.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalOutboundParcelLineEntity` | detail _(review)_ | `ClinicalOutboundParcelLineDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_outbound_parcel_wave.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalOutboundParcelWaveEntity` | core | `ClinicalOutboundParcelWaveCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_ownership_anchor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalOwnershipAnchorEntity` | core | `ClinicalOwnershipAnchorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_packing_anchor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalPackingAnchorEntity` | core | `ClinicalPackingAnchorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_partner_hub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalPartnerHubEntity` | core | `ClinicalPartnerHubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_partner_org_projection.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalPartnerOrgProjectionEntity` | core | `ClinicalPartnerOrgProjectionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_partner_person_projection.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalPartnerPersonProjectionEntity` | core | `ClinicalPartnerPersonProjectionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_transport_anchor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClinicalTransportAnchorEntity` | core | `ClinicalTransportAnchorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/entities/projection_demo_core.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ProjectionDemoCustomerEntity` | core | `ProjectionDemoCustomerCoreEntity` | carries its own identity, lifecycle or business fields |
| `ProjectionDemoOrderEntity` | core | `ProjectionDemoOrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/generalization_shapes/entities/generalization_entities.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `GeneralizationHeadEntity` | core | `GeneralizationHeadCoreEntity` | carries its own identity, lifecycle or business fields |
| `GeneralizationVariantAEntity` | spec | `GeneralizationVariantASpecEntity` | declares a Generalization, so it is variant data of its head |
| `GeneralizationVariantBEntity` | spec | `GeneralizationVariantBSpecEntity` | declares a Generalization, so it is variant data of its head |

### `packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_credential_merge.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IdentityCredentialMergeCorrelateEntity` | core | `IdentityCredentialMergeCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_credential_rotation_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IdentityCredentialRotationStubEntity` | core | `IdentityCredentialRotationStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_email_factor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IdentityEmailFactorEntity` | core | `IdentityEmailFactorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_federated_linkage.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IdentityFederatedLinkageEntity` | core | `IdentityFederatedLinkageCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_org_binding_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IdentityOrgBindingStubEntity` | core | `IdentityOrgBindingStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_person_hub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IdentityPersonHubEntity` | core | `IdentityPersonHubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_phone_factor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `IdentityPhoneFactorEntity` | core | `IdentityPhoneFactorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_bin_coordinate_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BinCoordinateStubEntity` | core | `BinCoordinateStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_crossdock_staging.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CrossDockStagingEntity` | core | `CrossDockStagingCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_disposition_advice.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DispositionAdviceEntity` | core | `DispositionAdviceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_facility_warehouse.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FacilityWarehouseEntity` | core | `FacilityWarehouseCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_lot_age_bucket.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LotAgeBucketEntity` | core | `LotAgeBucketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_lot_freeze_flag.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LotFreezeFlagEntity` | core | `LotFreezeFlagCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_lot_quality_hold.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LotQualityHoldEntity` | core | `LotQualityHoldCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_lot_snapshot_ledger.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LotSnapshotLedgerEntity` | core | `LotSnapshotLedgerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_mesh_bin_age.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `InvBinAgeCorrelateEntity` | core | `InvBinAgeCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_mesh_facility_crossdock.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `InvFacilityCrossdockBridgeEntity` | core | `InvFacilityCrossdockBridgeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_recall_signal.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RecallSignalEntity` | core | `RecallSignalCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_storage_aisle_row.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `StorageAisleRowEntity` | detail _(review)_ | `StorageAisleRowDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/logistics_mesh/entities/facility_handoff_manifest_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FacilityHandoffManifestEntity` | assoc _(review)_ | `FacilityHandoffManifestAssocEntity` | is named as a technical connection (module) and carries no lifecycle |

### `packages/aoa-demo/src/aoa/demo/model/logistics_mesh/entities/freight_waypoint_leg_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FreightWaypointLegEntity` | core | `FreightWaypointLegCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_batching_fence.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BatchingFenceEntity` | core | `BatchingFenceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_courier_attempt_ledger.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CourierAttemptLedgerEntity` | core | `CourierAttemptLedgerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_dedupe_correlation.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DedupeCorrelationEntity` | core | `DedupeCorrelationCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_dispatcher_cursor_shard.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DispatcherCursorShardEntity` | core | `DispatcherCursorShardCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_downstream_watermark.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DownstreamWatermarkEntity` | core | `DownstreamWatermarkCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_er_cycle_triangle_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `MsgDirectedCycleTriangleAEntity` | core | `MsgDirectedCycleTriangleACoreEntity` | carries its own identity, lifecycle or business fields |
| `MsgDirectedCycleTriangleBEntity` | core | `MsgDirectedCycleTriangleBCoreEntity` | carries its own identity, lifecycle or business fields |
| `MsgDirectedCycleTriangleCEntity` | core | `MsgDirectedCycleTriangleCCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_fanout_replay_cursor.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FanoutReplayCursorEntity` | core | `FanoutReplayCursorCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_hop_latency_sample.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `HopLatencySampleEntity` | core | `HopLatencySampleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_mesh_courier_replay.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `MsgCourierReplayCorrelateEntity` | core | `MsgCourierReplayCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_mesh_outbox_webhook.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `MsgOutboxWebhookCorrelateEntity` | core | `MsgOutboxWebhookCorrelateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_recipient_device_seen.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RecipientDeviceSeenEntity` | core | `RecipientDeviceSeenCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_replay_ticket.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ReplayTicketEntity` | core | `ReplayTicketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_throttle_lease.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ThrottleLeaseEntity` | core | `ThrottleLeaseCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_webhook_ingress_receipt.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `WebhookIngressReceiptEntity` | core | `WebhookIngressReceiptCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/msg_webhook_signature_envelope.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `WebhookSignatureEnvelopeEntity` | core | `WebhookSignatureEnvelopeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/messaging/entities/outbox_message.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OutboxMessageEntity` | core | `OutboxMessageCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/settlement_desks/entities/clearing_instruction_row_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ClearingInstructionRowEntity` | detail | `ClearingInstructionRowDetailEntity` | is named as a part of its owner (module) and carries no lifecycle |

### `packages/aoa-demo/src/aoa/demo/model/settlement_desks/entities/desk_lane_exposure_marker_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DeskLaneExposureMarkerEntity` | core | `DeskLaneExposureMarkerCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/audit_log_entry.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AuditLogEntryEntity` | detail _(review)_ | `AuditLogEntryDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/discount_application.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DiscountApplicationEntity` | core | `DiscountApplicationCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/fulfillment_task.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FulfillmentTaskEntity` | core | `FulfillmentTaskCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/invoice_record.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `InvoiceRecordEntity` | core | `InvoiceRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/payment_authorization.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `PaymentAuthorizationEntity` | core | `PaymentAuthorizationCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/payment_capture.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `PaymentCaptureEntity` | core | `PaymentCaptureCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/refund_request.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RefundRequestEntity` | core | `RefundRequestCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/return_request.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ReturnRequestEntity` | core | `ReturnRequestCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/sales_core.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CustomerAccountEntity` | core | `CustomerAccountCoreEntity` | carries its own identity, lifecycle or business fields |
| `SalesOrderEntity` | core | `SalesOrderCoreEntity` | declares Composite parts, so it owns them: an aggregate root |
| `SalesOrderLineEntity` | detail _(review)_ | `SalesOrderLineDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/shipment_parcel.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ShipmentParcelEntity` | core | `ShipmentParcelCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/shipment_tracking_event.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ShipmentTrackingEventEntity` | core | `ShipmentTrackingEventCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_cart_merge_trace.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CartMergeTraceEntity` | core | `CartMergeTraceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_er_cycle_ping_pong.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `StoreDirectedCyclePingEntity` | core | `StoreDirectedCyclePingCoreEntity` | carries its own identity, lifecycle or business fields |
| `StoreDirectedCyclePongEntity` | core | `StoreDirectedCyclePongCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_backorder_eta.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `BackorderEtaFacetEntity` | core | `BackorderEtaFacetCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_kit_explosion.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `KitExplosionLineEntity` | detail _(review)_ | `KitExplosionLineDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_pick_variance.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `PickVarianceRecordEntity` | core | `PickVarianceRecordCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_serial_trace.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LineSerialLotTraceEntity` | core | `LineSerialLotTraceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_shipment_piece.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LineShipmentPieceEntity` | detail _(review)_ | `LineShipmentPieceDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_substitution_hist.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SubstitutionHistoryEntity` | core | `SubstitutionHistoryCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_line_warranty_offer.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `WarrantyOfferFacetEntity` | core | `WarrantyOfferFacetCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_loyalty_earn_projection.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `LoyaltyEarnProjectionEntity` | core | `LoyaltyEarnProjectionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_mesh_customer_order_affinity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `StoreCustomerOrderAffinityEntity` | core | `StoreCustomerOrderAffinityCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_mesh_invoice_line_tie.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `StoreInvoiceLineTieEntity` | core | `StoreInvoiceLineTieCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_mesh_line_parcel_pick.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `StoreLineParcelPickEntity` | core | `StoreLineParcelPickCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_mesh_order_invoice_bridge.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `StoreOrderInvoiceBridgeEntity` | core | `StoreOrderInvoiceBridgeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_mesh_order_parcel_handoff.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `StoreOrderParcelHandoffEntity` | core | `StoreOrderParcelHandoffCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_address_verification.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `AddressVerificationTrailEntity` | core | `AddressVerificationTrailCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_channel_attribution.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderChannelAttributionEntity` | core | `OrderChannelAttributionCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_compliance_review.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ComplianceReviewQueueEntity` | core | `ComplianceReviewQueueCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_deposit_allocation.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `DepositAllocationEntity` | core | `DepositAllocationCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_dual_entry_origin.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderDualEntryOriginTraceEntity` | core | `OrderDualEntryOriginTraceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_fraud_challenge.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `FraudChallengeTicketEntity` | core | `FraudChallengeTicketCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_geo_fence.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderGeoFenceEntity` | core | `OrderGeoFenceCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_gift_wrap.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `GiftWrapAddonEntity` | core | `GiftWrapAddonCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_packing_slip.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `PackingSlipEntity` | core | `PackingSlipCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_revenue_schedule.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RevenueDeferralScheduleEntity` | core | `RevenueDeferralScheduleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_risk_score.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderRiskScoreEntity` | core | `OrderRiskScoreCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_shipment_estimate.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ShipmentEstimateEntity` | core | `ShipmentEstimateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_split_bill.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SplitBillAllocationEntity` | core | `SplitBillAllocationCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_tax_jurisdiction.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `OrderTaxJurisdictionSnapshotEntity` | core | `OrderTaxJurisdictionSnapshotCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/store/entities/tax_line.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `TaxLineEntity` | detail _(review)_ | `TaxLineDetailEntity` | is named as a part of its owner |

### `packages/aoa-demo/src/aoa/demo/model/support/entities/support_comment_thread_stub.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SupportCommentThreadStubEntity` | core | `SupportCommentThreadStubCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/support/entities/support_mesh_ticket_observer.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SupportTicketParticipantPairEntity` | core | `SupportTicketParticipantPairCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/support/entities/support_participant_row.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SupportParticipantEntity` | core | `SupportParticipantCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/support/entities/support_sla_interval.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SupportSlaIntervalEntity` | core | `SupportSlaIntervalCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/support/entities/support_ticket_aggregate.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SupportTicketAggregateEntity` | core | `SupportTicketAggregateCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/entities/routed_observation_slice_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `RoutedObservationSliceEntity` | detail | `RoutedObservationSliceDetailEntity` | is named as a part of its owner (module) and carries no lifecycle |

### `packages/aoa-demo/src/aoa/demo/model/telemetry_pipeline/entities/telemetry_ingest_envelope_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `TelemetryIngestEnvelopeEntity` | core | `TelemetryIngestEnvelopeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-fastapi-adapter/tests/support/domain_model.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SampleEntity` | core | `SampleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-maxitor/src/aoa/maxitor/model/core/entities/node_entity.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `NodeEntity` | core | `NodeCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-mcp-adapter/tests/support/domain_model.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SampleEntity` | core | `SampleCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-ocel/examples/01_ocel_export.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `CustomerEntity` | core | `CustomerCoreEntity` | carries its own identity, lifecycle or business fields |
| `OrderEntity` | core | `OrderCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-ocel/tests/plugin/test_ocel_plugin.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `ChildEntity` | assoc | `ChildAssocEntity` | carries only participant references and service fields |
| `PolicyEntity` | core | `PolicyCoreEntity` | carries its own identity, lifecycle or business fields |

### `packages/aoa-ocel/tests/support/domain_model.py`

| Class | Kind | New name | Reason |
| --- | --- | --- | --- |
| `SampleEntity` | core | `SampleCoreEntity` | carries its own identity, lifecycle or business fields |

