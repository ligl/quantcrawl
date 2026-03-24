from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

F = TypeVar("F", bound=Callable[..., object])


def retryable(max_attempts: int = 3, base_seconds: float = 0.5) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        wrapped = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential_jitter(initial=base_seconds),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )(func)
        return wrapped  # type: ignore[return-value]

    return decorator
