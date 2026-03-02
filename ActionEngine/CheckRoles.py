from typing import List, Union

class CheckRoles:
    NONE = "NO_ROLE"
    ANY = "ANY_ROLE"

    def __init__(self, spec: Union[str, List[str]]):
        self.spec = spec

    def __call__(self, cls):
        cls._role_spec = self.spec
        return cls