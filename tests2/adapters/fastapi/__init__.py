# tests2/adapters/fastapi/__init__.py
"""
Tests for the FastAPI adapter layer.

Covers FastApiAdapter (registration, build, fluent chain, health check,
exception handlers, OpenAPI metadata), FastApiRouteRecord (HTTP-specific
validation, field defaults, method normalization), and OpenAPI schema
generation from registered routes.

Test modules:
    test_fastapi_adapter.py       — Adapter construction, route registration via
                                    post/get/put/delete/patch, build() producing
                                    a FastAPI app, fluent chaining, health check
                                    endpoint, exception handler registration.
    test_fastapi_route_record.py  — HTTP-specific validation (method from allowed
                                    set, path starts with '/'), field defaults,
                                    method normalization to uppercase, inherited
                                    BaseRouteRecord invariants.
    test_fastapi_openapi.py       — OpenAPI schema includes registered routes with
                                    correct paths, methods, tags, summary, response
                                    models, and Pydantic field descriptions.
"""
