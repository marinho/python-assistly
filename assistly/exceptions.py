class AssistlyError(BaseException): pass

class ResourceNotFound(AssistlyError): pass
class AuthenticationError(AssistlyError): pass
class TemporarilyUnavailable(AssistlyError): pass
class InvalidReturn(AssistlyError): pass
