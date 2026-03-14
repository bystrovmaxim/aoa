from typing import Optional, Any
from .CredentialExtractor import CredentialExtractor
from .Authenticator import Authenticator
from .ContextAssembler import ContextAssembler
from ..Context import Context, RequestInfo


class AuthCoordinator:
    def __init__(
        self,
        extractor: CredentialExtractor,
        authenticator: Authenticator,
        assembler: ContextAssembler,
    ) -> None:
        self.extractor = extractor
        self.authenticator = authenticator
        self.assembler = assembler

    def process(self, request_data: Any) -> Optional[Context]:
        credentials = self.extractor.extract(request_data)
        if not credentials:
            return None
        user_info = self.authenticator.authenticate(credentials)
        if not user_info:
            return None
        metadata = self.assembler.assemble(request_data)
        req_info = RequestInfo(**metadata)
        return Context(user=user_info, request=req_info, environment=None)
