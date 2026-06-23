# packages/aoa-fastapi-adapter/src/aoa/fastapi/query_field_before/__init__.py
"""
Reusable Pydantic ``BeforeValidator`` helpers for FastAPI query-shaped inputs.

Use with action ``Params`` fields typed as ``list[str]``. Prefer :data:`QUERY_STR_LIST_BEFORE`
for OpenAPI query arrays (repeated keys, no delimiter splitting inside values).
"""

from aoa.fastapi.query_field_before.query_str_list import (
    QUERY_STR_LIST_BEFORE,
    coerce_query_str_list,
)

__all__ = [
    "QUERY_STR_LIST_BEFORE",
    "coerce_query_str_list",
]
