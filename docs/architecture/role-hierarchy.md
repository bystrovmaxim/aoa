# Иерархия ролей

Каждый уровень — **отдельный модуль** в `src/action_machine/intents/auth/`:

```
BaseRole (ABC)              → base_role.py
├── SystemRole (ABC)        → system_role.py
│   ├── NoneRole (sealed)   → none_role.py
│   └── AnyRole (sealed)    → any_role.py
└── ApplicationRole (ABC)     → application_role.py
    └── …                   → прикладные роли проекта
```

- **SystemRole** / **NoneRole** / **AnyRole** — только для `@check_roles`, не для `UserInfo.roles`.
- **ApplicationRole** — корень типов, которые допускаются в `UserInfo.roles`.

Импликация прав (кто проходит `@check_roles(X)`) задаётся **наследованием** (MRO), отдельного поля композиции ролей нет.
