# ActionEngine/Context.py
from typing import List, Optional

class Context:
    """Контекст выполнения запроса."""
    def __init__(self, user_id: Optional[str] = None, roles: Optional[List[str]] = None):
        self.user_id = user_id
        self.roles = roles if roles is not None else []