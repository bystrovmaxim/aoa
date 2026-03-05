from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class RequestInfo:
    trace_id: Optional[str] = None
    request_timestamp: Optional[datetime] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    full_url: Optional[str] = None
    client_ip: Optional[str] = None
    protocol: Optional[str] = None
    user_agent: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)