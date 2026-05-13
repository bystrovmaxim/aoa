# packages/aoa-action-machine/src/aoa/action_machine/graph_model/graph_json_schema.py
"""JSON Schema for ActionMachine graph export via :class:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator`.

Pass :data:`GRAPH_JSON_SCHEMA` to :meth:`NodeGraphCoordinator.build` as ``export_json_schema`` so
:meth:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator.to_json` can validate payloads without
``aoa-graph`` owning ActionMachine-specific types.

Sourced from ``archive/plan/CURRENT.md`` (appendix) with alignment fixes
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
        "$ref": "#/$defs/vertex"
      },
      "uniqueItems": true
    },
    "edges": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/link"
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
    "vertex": {
      "oneOf": [
        {
          "$ref": "#/$defs/action"
        },
        {
          "$ref": "#/$defs/application"
        },
        {
          "$ref": "#/$defs/domain"
        },
        {
          "$ref": "#/$defs/entity"
        },
        {
          "$ref": "#/$defs/resource"
        },
        {
          "$ref": "#/$defs/params"
        },
        {
          "$ref": "#/$defs/result"
        },
        {
          "$ref": "#/$defs/field"
        },
        {
          "$ref": "#/$defs/property_field"
        },
        {
          "$ref": "#/$defs/regular_aspect"
        },
        {
          "$ref": "#/$defs/summary_aspect"
        },
        {
          "$ref": "#/$defs/compensator"
        },
        {
          "$ref": "#/$defs/error_handler"
        },
        {
          "$ref": "#/$defs/checker"
        },
        {
          "$ref": "#/$defs/required_context_vertex"
        },
        {
          "$ref": "#/$defs/lifecycle_vertex"
        },
        {
          "$ref": "#/$defs/state"
        },
        {
          "$ref": "#/$defs/sensitive"
        },
        {
          "$ref": "#/$defs/role"
        }
      ]
    },
    "row": {
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
    "action": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "application": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "domain": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "entity": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "resource": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "params": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "result": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "field": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "property_field": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "regular_aspect": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "summary_aspect": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "compensator": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "error_handler": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "checker": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "required_context_vertex": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "lifecycle_vertex": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "state": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "sensitive": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "role": {
      "allOf": [
        {
          "$ref": "#/$defs/row"
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
    "link_row": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "source_id",
        "target_id",
        "type",
        "relationship",
        "is_dag",
        "properties"
      ],
      "properties": {
        "source_id": {
          "type": "string",
          "minLength": 1
        },
        "target_id": {
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
    "link": {
      "oneOf": [
        {
          "$ref": "#/$defs/empty_properties"
        },
        {
          "$ref": "#/$defs/depends"
        },
        {
          "$ref": "#/$defs/connection"
        },
        {
          "$ref": "#/$defs/required_context_binding"
        },
        {
          "$ref": "#/$defs/entity_relation"
        },
        {
          "$ref": "#/$defs/entity_view"
        },
        {
          "$ref": "#/$defs/lifecycle_binding"
        },
        {
          "$ref": "#/$defs/lifecycle_state"
        },
        {
          "$ref": "#/$defs/lifecycle_transition"
        },
        {
          "$ref": "#/$defs/sensitive_or_state"
        }
      ]
    },
    "empty_properties": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "depends": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "connection": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "required_context_binding": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "entity_relation": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "entity_view": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "lifecycle_binding": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "lifecycle_state": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "lifecycle_transition": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
    "sensitive_or_state": {
      "allOf": [
        {
          "$ref": "#/$defs/link_row"
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
