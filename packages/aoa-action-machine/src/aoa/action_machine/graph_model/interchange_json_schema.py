# packages/aoa-action-machine/src/aoa/action_machine/graph_model/interchange_json_schema.py
"""JSON Schema for ActionMachine interchange export via :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`.

Pass :data:`GRAPH_JSON_SCHEMA` to :meth:`NodeGraphCoordinator.build` as ``export_json_schema`` so
:meth:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator.to_json` can validate payloads without
``aoa-graph`` owning ActionMachine-specific types.

Sourced from ``archive/plan/CURRENT.md`` (appendix) with interchange alignment fixes
(``Field`` node properties, ``Lifecycle`` / ``@required_context`` / ``@check_roles`` edge names).
"""

from __future__ import annotations

import json
from typing import Any

_GRAPH_JSON_SCHEMA_RAW = r"""
  {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://aoa.local/schemas/node-graph-export.schema.json",
    "title": "AOA node graph JSON export",
    "type": "object",
    "additionalProperties": false,
    "required": [
      "schema_version",
      "nodes",
      "edges"
    ],
    "properties": {
      "schema_version": {
        "const": "1.0"
      },
      "nodes": {
        "type": "array",
        "items": {
          "$ref": "#/$defs/node"
        },
        "uniqueItems": true
      },
      "edges": {
        "type": "array",
        "items": {
          "$ref": "#/$defs/edge"
        }
      }
    },
    "$defs": {
      "json_value": {
        "oneOf": [
          {
            "type": "null"
          },
          {
            "type": "boolean"
          },
          {
            "type": "number"
          },
          {
            "type": "string"
          },
          {
            "type": "array",
            "items": {
              "$ref": "#/$defs/json_value"
            }
          },
          {
            "type": "object",
            "additionalProperties": {
              "$ref": "#/$defs/json_value"
            }
          }
        ]
      },
      "base_properties": {
        "type": "object",
        "additionalProperties": {
          "$ref": "#/$defs/json_value"
        }
      },
      "node": {
        "oneOf": [
          {
            "$ref": "#/$defs/node_action"
          },
          {
            "$ref": "#/$defs/node_application"
          },
          {
            "$ref": "#/$defs/node_domain"
          },
          {
            "$ref": "#/$defs/node_entity"
          },
          {
            "$ref": "#/$defs/node_resource"
          },
          {
            "$ref": "#/$defs/node_params"
          },
          {
            "$ref": "#/$defs/node_result"
          },
          {
            "$ref": "#/$defs/node_field"
          },
          {
            "$ref": "#/$defs/node_property_field"
          },
          {
            "$ref": "#/$defs/node_regular_aspect"
          },
          {
            "$ref": "#/$defs/node_summary_aspect"
          },
          {
            "$ref": "#/$defs/node_compensator"
          },
          {
            "$ref": "#/$defs/node_error_handler"
          },
          {
            "$ref": "#/$defs/node_checker"
          },
          {
            "$ref": "#/$defs/node_required_context"
          },
          {
            "$ref": "#/$defs/node_lifecycle"
          },
          {
            "$ref": "#/$defs/node_state"
          },
          {
            "$ref": "#/$defs/node_sensitive"
          },
          {
            "$ref": "#/$defs/node_role"
          }
        ]
      },
      "node_base": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "id",
          "type",
          "label",
          "properties"
        ],
        "properties": {
          "id": {
            "type": "string",
            "minLength": 1
          },
          "type": {
            "type": "string",
            "minLength": 1
          },
          "label": {
            "type": "string",
            "minLength": 1
          },
          "properties": {
            "$ref": "#/$defs/base_properties"
          }
        }
      },
      "node_action": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Action"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "description"
                ],
                "properties": {
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_application": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Application"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "name",
                  "description"
                ],
                "properties": {
                  "name": {
                    "type": "string"
                  },
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_domain": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Domain"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "name",
                  "description"
                ],
                "properties": {
                  "name": {
                    "type": "string"
                  },
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_entity": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Entity"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "description"
                ],
                "properties": {
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_resource": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Resource"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "description"
                ],
                "properties": {
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_params": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Params"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "maxProperties": 0
              }
            }
          }
        ]
      },
      "node_result": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Result"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "maxProperties": 0
              }
            }
          }
        ]
      },
      "node_field": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Field"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "required",
                  "description",
                  "json_schema_value",
                  "entity_schema"
                ],
                "properties": {
                  "required": {
                    "type": "boolean"
                  },
                  "description": {
                    "type": "string"
                  },
                  "json_schema_value": {
                    "type": "boolean"
                  },
                  "entity_schema": {
                    "type": "boolean"
                  },
                  "json_schema_name": {
                    "type": "string"
                  },
                  "json_schema": {
                    "$ref": "#/$defs/json_value"
                  }
                }
              }
            }
          }
        ]
      },
      "node_property_field": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "PropertyField"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "required",
                  "entity_schema"
                ],
                "properties": {
                  "required": {
                    "type": "boolean"
                  },
                  "entity_schema": {
                    "type": "boolean"
                  }
                }
              }
            }
          }
        ]
      },
      "node_regular_aspect": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "RegularAspect"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "description"
                ],
                "properties": {
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_summary_aspect": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "SummaryAspect"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "description"
                ],
                "properties": {
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_compensator": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Compensator"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "description": {
                    "type": "string"
                  },
                  "target_aspect_name": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_error_handler": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "ErrorHandler"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "description": {
                    "type": "string"
                  },
                  "exception_types": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        ]
      },
      "node_checker": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Checker"
              },
              "properties": {
                "type": "object",
                "additionalProperties": {
                  "$ref": "#/$defs/json_value"
                },
                "required": [
                  "TypeChecker",
                  "required"
                ],
                "properties": {
                  "TypeChecker": {
                    "type": "string"
                  },
                  "required": {
                    "type": "boolean"
                  }
                }
              }
            }
          }
        ]
      },
      "node_required_context": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "RequiredContext"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "key"
                ],
                "properties": {
                  "key": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_lifecycle": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Lifecycle"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "field_name"
                ],
                "properties": {
                  "field_name": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_state": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "enum": [
                  "StateInitial",
                  "StateIntermediate",
                  "StateFinal"
                ]
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "lifecycle_class_id",
                  "state_key"
                ],
                "properties": {
                  "lifecycle_class_id": {
                    "type": "string"
                  },
                  "state_key": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "node_sensitive": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Sensitive"
              },
              "properties": {
                "$ref": "#/$defs/base_properties"
              }
            }
          }
        ]
      },
      "node_role": {
        "allOf": [
          {
            "$ref": "#/$defs/node_base"
          },
          {
            "properties": {
              "type": {
                "const": "Role"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "role_mode"
                ],
                "properties": {
                  "role_mode": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "relationship": {
        "type": "string",
        "enum": [
          "Access",
          "Aggregation",
          "Assignment",
          "Association",
          "Composition",
          "Flow",
          "Generalization",
          "Realization",
          "Serving",
          "Specialization",
          "Triggering"
        ]
      },
      "edge_base": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "source_node_id",
          "target_node_id",
          "type",
          "relationship",
          "is_dag",
          "properties"
        ],
        "properties": {
          "source_node_id": {
            "type": "string",
            "minLength": 1
          },
          "target_node_id": {
            "type": "string",
            "minLength": 1
          },
          "type": {
            "type": "string",
            "minLength": 1
          },
          "relationship": {
            "$ref": "#/$defs/relationship"
          },
          "is_dag": {
            "type": "boolean"
          },
          "properties": {
            "$ref": "#/$defs/base_properties"
          }
        }
      },
      "edge": {
        "oneOf": [
          {
            "$ref": "#/$defs/edge_empty_properties"
          },
          {
            "$ref": "#/$defs/edge_depends"
          },
          {
            "$ref": "#/$defs/edge_connection"
          },
          {
            "$ref": "#/$defs/edge_required_context"
          },
          {
            "$ref": "#/$defs/edge_entity_relation"
          },
          {
            "$ref": "#/$defs/edge_entity_view"
          },
          {
            "$ref": "#/$defs/edge_lifecycle"
          },
          {
            "$ref": "#/$defs/edge_lifecycle_state"
          },
          {
            "$ref": "#/$defs/edge_lifecycle_transition"
          },
          {
            "$ref": "#/$defs/edge_sensitive_or_state"
          }
        ]
      },
      "edge_empty_properties": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "enum": [
                  "application",
                  "domain",
                  "generic:params",
                  "generic:result",
                  "@check_roles",
                  "@regular_aspect",
                  "@summary_aspect",
                  "@compensate",
                  "@on_error",
                  "@result_checker",
                  "entity_schema",
                  "field",
                  "property"
                ]
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "maxProperties": 0
              }
            }
          }
        ]
      },
      "edge_depends": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "@depends"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "description"
                ],
                "properties": {
                  "description": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_connection": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "@connection"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "key"
                ],
                "properties": {
                  "key": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_required_context": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "@required_context"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "key"
                ],
                "properties": {
                  "key": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_entity_relation": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "entity_relation"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "field_name",
                  "relation_type",
                  "cardinality",
                  "description",
                  "has_inverse",
                  "deprecated"
                ],
                "properties": {
                  "field_name": {
                    "type": "string"
                  },
                  "relation_type": {
                    "type": "string"
                  },
                  "cardinality": {
                    "type": "string"
                  },
                  "description": {
                    "type": "string"
                  },
                  "has_inverse": {
                    "type": "boolean"
                  },
                  "deprecated": {
                    "type": "boolean"
                  },
                  "inverse_entity_id": {
                    "type": "string"
                  },
                  "inverse_field": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_entity_view": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "entity_view"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "field_name"
                ],
                "properties": {
                  "field_name": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_lifecycle": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "lifecycle"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "field_name"
                ],
                "properties": {
                  "field_name": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_lifecycle_state": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "lifecycle_contains_state"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "state_key"
                ],
                "properties": {
                  "state_key": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_lifecycle_transition": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "const": "lifecycle_transition"
              },
              "properties": {
                "type": "object",
                "additionalProperties": false,
                "required": [
                  "from_state",
                  "to_state"
                ],
                "properties": {
                  "from_state": {
                    "type": "string"
                  },
                  "to_state": {
                    "type": "string"
                  }
                }
              }
            }
          }
        ]
      },
      "edge_sensitive_or_state": {
        "allOf": [
          {
            "$ref": "#/$defs/edge_base"
          },
          {
            "properties": {
              "type": {
                "enum": [
                  "sensitive",
                  "state"
                ]
              },
              "properties": {
                "$ref": "#/$defs/base_properties"
              }
            }
          }
        ]
      }
    }
  }
"""

GRAPH_JSON_SCHEMA: dict[str, Any] = json.loads(_GRAPH_JSON_SCHEMA_RAW)
