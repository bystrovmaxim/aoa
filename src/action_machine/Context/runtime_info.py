# src/action_machine/Context/runtime_info.py
"""
Компонент контекста, содержащий информацию об окружении, в котором выполняется код.
Заполняется один раз при старте приложения и затем копируется в каждый контекст.
Реализует ReadableDataProtocol через ReadableMixin для обеспечения dict-подобного доступа.
"""

from dataclasses import dataclass, field
from typing import Any

from action_machine.core.readable_mixin import ReadableMixin


@dataclass
class RuntimeInfo(ReadableMixin):
    """
    Информация об окружении выполнения.

    Позволяет идентифицировать, на каком сервере, в какой версии и в каком окружении
    выполняется действие. Особенно полезно при горизонтальном масштабировании и анализе логов.

    Благодаря наследованию от ReadableMixin, объект RuntimeInfo поддерживает dict-подобный доступ:
    - runtime["hostname"], runtime.get("service_name"), runtime.keys() и т.д.

    Атрибуты:
        hostname: Имя хоста (контейнера или сервера).
        service_name: Название сервиса (например, "youtrack-api").
        service_version: Версия сервиса.
        container_id: Идентификатор Docker-контейнера (если есть).
        pod_name: Имя пода в Kubernetes (если есть).
        extra: Дополнительные поля, специфичные для инфраструктуры.

    Пример:
        >>> runtime = RuntimeInfo(
        ...     hostname="pod-xyz-123",
        ...     service_name="youtrack-api",
        ...     service_version="1.2.3"
        ... )
        >>> runtime["hostname"]
        'pod-xyz-123'
    """

    hostname: str | None = None
    service_name: str | None = None
    service_version: str | None = None
    container_id: str | None = None
    pod_name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)