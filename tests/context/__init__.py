# tests/context/__init__.py
"""
Тесты компонентов контекста выполнения ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Покрывает все компоненты контекста, передаваемого в машину при выполнении
действия:

- UserInfo — информация о пользователе (user_id, roles, extra).
  Dataclass с ReadableMixin. Используется для проверки ролей
  в ActionProductMachine._check_action_roles().

- RequestInfo — метаданные входящего запроса (trace_id, request_path,
  client_ip и др.). Dataclass с ReadableMixin. Заполняется адаптером
  или AuthCoordinator при обработке запроса.

- RuntimeInfo — информация об окружении выполнения (hostname,
  service_name, service_version). Dataclass с ReadableMixin.
  Заполняется один раз при старте приложения.

- Context — корневой объект контекста, объединяющий UserInfo,
  RequestInfo и RuntimeInfo. Наследует ReadableMixin, поддерживает
  resolve по вложенным компонентам: context.resolve("user.roles"),
  context.resolve("request.trace_id").

Все компоненты наследуют ReadableMixin, что обеспечивает dict-подобный
доступ (keys, values, items, __getitem__, __contains__, get) и навигацию
по вложенным объектам через resolve().
"""
