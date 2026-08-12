import httpx


class ProviderError(Exception):
    """A user-facing failure talking to an external provider (API key, rate limit, network)."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(message)


def wrap_httpx_error(provider: str, exc: Exception) -> ProviderError:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return ProviderError(provider, f"{provider}: invalid or missing API key — check Settings.")
        if status == 429:
            return ProviderError(provider, f"{provider}: rate limit reached — try again later.")
        return ProviderError(provider, f"{provider}: request failed (HTTP {status}).")
    if isinstance(exc, httpx.TimeoutException):
        return ProviderError(provider, f"{provider} timed out — try again shortly.")
    if isinstance(exc, httpx.RequestError):
        return ProviderError(provider, f"{provider} is unreachable right now.")
    return ProviderError(provider, f"{provider}: unexpected error ({exc}).")
