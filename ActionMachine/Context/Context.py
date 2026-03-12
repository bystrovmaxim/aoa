from typing import Optional, Dict, Any
from .UserInfo import UserInfo
from .RequestInfo import RequestInfo
from .EnvironmentInfo import EnvironmentInfo

class Context:
    def __init__(
        self,
        user: Optional[UserInfo] = None,
        request: Optional[RequestInfo] = None,
        environment: Optional[EnvironmentInfo] = None
    ) -> None:
        self.user = user or UserInfo()
        self.request = request or RequestInfo()
        self.environment = environment or EnvironmentInfo()
        self._extra: Dict[str, Any] = {}

    def set_extra(self, key: str, value: Any) -> None:
        self._extra[key] = value
        setattr(self, key, value)

    def get_extra(self, key: str, default: Any = None) -> Any:
        return self._extra.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        result['user_id'] = self.user.user_id
        result['roles'] = self.user.roles
        result.update(self.user.extra)
        result['trace_id'] = self.request.trace_id
        if self.request.request_timestamp:
            result['request_timestamp'] = self.request.request_timestamp.isoformat()
        result['request_path'] = self.request.request_path
        result['request_method'] = self.request.request_method
        result['full_url'] = self.request.full_url
        result['client_ip'] = self.request.client_ip
        result['protocol'] = self.request.protocol
        result['user_agent'] = self.request.user_agent
        result.update(self.request.extra)
        result['hostname'] = self.environment.hostname
        result['service_name'] = self.environment.service_name
        result['service_version'] = self.environment.service_version
        result['environment'] = self.environment.environment
        result['container_id'] = self.environment.container_id
        result['pod_name'] = self.environment.pod_name
        result.update(self.environment.extra)
        result.update(self._extra)
        return result