from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class UserInfo:
    user_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)