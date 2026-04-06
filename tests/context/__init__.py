# tests/context/__init__.py
"""
Тесты компонентов контекста выполнения ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Покрывает все компоненты контекста, передаваемого в машину при выполнении
действия:

- UserInfo — информация о пользователе (user_id, roles).
  Наследник BaseSchema (frozen, forbid) [1]. Используется для проверки
  ролей в ActionProductMachine._check_action_roles().

- RequestInfo — метаданные входящего запроса (trace_id, request_path,
  client_ip и др.). Наследник BaseSchema (frozen, forbid).
  Заполняется адаптером или AuthCoordinator при обработке запроса.

- RuntimeInfo — информация об окружении выполнения (hostname,
  service_name, service_version). Наследник BaseSchema (frozen, forbid).
  Заполняется один раз при старте приложения.

- Context — корневой объект контекста, объединяющий UserInfo,
  RequestInfo и RuntimeInfo. Наследник BaseSchema (frozen, forbid),
  поддерживает resolve по вложенным компонентам:
  context.resolve("user.roles"), context.resolve("request.trace_id") [2].

Все компоненты наследуют BaseSchema [2], что обеспечивает dict-подобный
доступ (keys, values, items, __getitem__, __contains__, get) и навигацию
по вложенным объектам через resolve().
"""
