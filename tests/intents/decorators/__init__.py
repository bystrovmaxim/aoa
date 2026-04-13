# tests/intents/decorators/__init__.py
"""
Tests for ActionMachine decorators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers class-level and method-level decorators:

Class-level:
- @meta(description, domain) — description and domain. Writes _meta_info. Required
  for Actions with aspects and for ResourceManager.
- @depends(cls, factory, description) — dependency declaration. Writes DependencyInfo
  to cls._depends_info.
- @connection(cls, key, description) — external resource connection. Writes
  ConnectionInfo to cls._connection_info.

Method-level:
- @regular_aspect(description) — pipeline business step. Writes _new_aspect_meta with
  type="regular".
- @summary_aspect(description) — final pipeline step. Writes _new_aspect_meta with
  type="summary".
- @sensitive(enabled, max_chars, char, max_percent) — masks sensitive data in logs.
  Writes _sensitive_config on the property getter.

@check_roles is covered in tests/intents/auth/test_check_roles_class_roles.py.

Each test module checks:
1. Correct metadata for valid arguments.
2. TypeError/ValueError for invalid arguments.
3. TypeError when applied to an invalid target.
4. Integration with MetadataBuilder and runtime metadata.
"""
