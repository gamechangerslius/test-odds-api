class ProviderClientError(RuntimeError):
    """Base error for provider client issues."""


class ProviderRequestError(ProviderClientError):
    """Network or HTTP-level error when calling a provider."""


class ProviderResponseError(ProviderClientError):
    """Response payload missing expected structure or invalid format."""
