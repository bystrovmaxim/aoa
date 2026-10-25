# FR-008 review — no object rule repeats the role check

**Date**: 2026-10-24
**Requirement**: FR-008 — `@access_decide` must not repeat the check `@check_roles` already performs:
no `issubclass` against a role type, no role-mode filtering, no role helper.

## Search

```text
grep -rlE "@access_decide" --include=*.py packages examples
  → 44 files, then
grep -nE "issubclass\(|RoleMode|has_role"  over each of those files
```

## Result

The role-matching tokens appear only in three production modules, none of which is an object rule:

| File | `issubclass`/`RoleMode` use | Verdict |
| --- | --- | --- |
| `intents/access_control/roles.py` | `issubclass(user_role, required)` and `RoleMode.SILENCED` filtering | the role layer itself — the correct owner |
| `intents/check_roles/check_roles_decorator.py` | `issubclass(spec, BaseRole)` and `RoleMode.UNUSED`/`DEPRECATED` | declaration validation — the correct owner |
| `intents/access_decide/access_decide_signature.py` | `issubclass(actual, expected)`, `issubclass(args[1], BaseResource)`, `issubclass(one, Verdict)` | signature checking of the object rule's own parameters and return type, not role matching |

Three test modules use `issubclass` for their own, unrelated purpose (`BasePluginEvent`, `BaseAction`),
again not roles.

No `@access_decide` method body anywhere calls `issubclass` against a role type, filters by
`RoleMode`, or calls a role helper — and no `has_role` helper exists.

The new `RolesAwareAction` in `test_access_decide_context.py` reads the caller's roles through the
declared `user.roles` key and tests membership (`AdminRole not in ctx.get("user.roles")`), which is
a role fact the `GuestRole` declaration cannot express — not a repetition of the declaration's own
match.

## Conclusion

No object rule repeats the check its own declaration performs.
