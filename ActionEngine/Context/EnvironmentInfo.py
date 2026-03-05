from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class EnvironmentInfo:
    hostname: Optional[str] = None
    service_name: Optional[str] = None
    service_version: Optional[str] = None
    environment: Optional[str] = None
    container_id: Optional[str] = None
    pod_name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)