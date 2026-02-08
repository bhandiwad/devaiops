from adapters.errors import AdapterAuthError, AdapterTimeoutError, AdapterTransientError, AdapterValidationError


def test_adapter_error_retryability_taxonomy():
    assert AdapterTimeoutError().retryable is True
    assert AdapterTransientError().retryable is True
    assert AdapterAuthError().retryable is False
    assert AdapterValidationError().retryable is False
