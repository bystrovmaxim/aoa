"""
Компонент контекста, содержащий информацию об окружении, в котором выполняется код.
Заполняется один раз при старте приложения и затем копируется в каждый контекст.
Реализует ReadableDataProtocol через ReadableMixin для обеспечения dict-подобного доступа.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from ActionMachine.Core.ReadableMixin import ReadableMixin


@dataclass
class EnvironmentInfo(ReadableMixin):
    """
    Информация об окружении выполнения.

    Позволяет идентифицировать, на каком сервере, в какой версии и в каком окружении
    выполняется действие. Особенно полезно при горизонтальном масштабировании и анализе логов.

    Благодаря наследованию от ReadableMixin, объект EnvironmentInfo поддерживает dict-подобный доступ:
    - env["hostname"], env.get("service_name"), "environment" in env, env.keys() и т.д.

    Атрибуты:
        hostname: Имя хоста (контейнера или сервера).
        service_name: Название сервиса (например, "youtrack-api").
        service_version: Версия сервиса.
        environment: Окружение ("dev", "staging", "production").
        container_id: Идентификатор Docker-контейнера (если есть).
        pod_name: Имя пода в Kubernetes (если есть).
        extra: Дополнительные поля, специфичные для инфраструктуры.

    Пример:
        >>> env = EnvironmentInfo(
        ...     hostname="pod-xyz-123",
        ...     service_name="youtrack-api",
        ...     service_version="1.2.3",
        ...     environment="production"
        ... )
        >>> env["hostname"]
        'pod-xyz-123'
    """
    hostname: Optional[str] = None
    service_name: Optional[str] = None
    service_version: Optional[str] = None
    environment: Optional[str] = None
    container_id: Optional[str] = None
    pod_name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)