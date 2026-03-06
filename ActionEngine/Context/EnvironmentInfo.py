# ActionEngine/Context/EnvironmentInfo.py
"""
Компонент контекста, содержащий информацию об окружении, в котором выполняется код.
Заполняется один раз при старте приложения и затем копируется в каждый контекст.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class EnvironmentInfo:
    """
    Информация об окружении выполнения.

    Позволяет идентифицировать, на каком сервере, в какой версии и в каком окружении
    выполняется действие. Особенно полезно при горизонтальном масштабировании и анализе логов.

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
    """
    hostname: Optional[str] = None
    service_name: Optional[str] = None
    service_version: Optional[str] = None
    environment: Optional[str] = None
    container_id: Optional[str] = None
    pod_name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)