from typing import List, Union, Optional

class CheckRoles:
    NONE = "NO_ROLE"
    ANY = "ANY_ROLE"

    def __init__(self, spec: Union[str, List[str]], desc: Optional[str]) -> None:
        self.spec = spec
        self.desc = desc

    def __call__(self, cls: type) -> type:
        cls._role_spec = self.spec  # type: ignore
        return cls