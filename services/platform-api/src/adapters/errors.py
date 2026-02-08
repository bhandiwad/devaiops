from __future__ import annotations


class AdapterError(Exception):
    def __init__(self, message: str, *, retryable: bool = False, code: str = "adapter_error") -> None:
        super().__init__(message)
        self.retryable = retryable
        self.code = code


class AdapterTimeoutError(AdapterError):
    def __init__(self, message: str = "adapter timeout") -> None:
        super().__init__(message, retryable=True, code="timeout")


class AdapterAuthError(AdapterError):
    def __init__(self, message: str = "adapter authentication failure") -> None:
        super().__init__(message, retryable=False, code="auth")


class AdapterValidationError(AdapterError):
    def __init__(self, message: str = "adapter validation failure") -> None:
        super().__init__(message, retryable=False, code="validation")


class AdapterTransientError(AdapterError):
    def __init__(self, message: str = "adapter transient failure") -> None:
        super().__init__(message, retryable=True, code="transient")
