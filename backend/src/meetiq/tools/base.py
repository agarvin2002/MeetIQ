import asyncio
import functools
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from meetiq.config.settings import settings
from meetiq.core.logging import logger


@dataclass
class ToolResult:
    """
    Standard return shape for every tool.
    The agent always receives this — even on failure — so it never crashes.
    """
    success: bool
    data: str                  # The actual content (text, JSON string, etc.)
    source: str = ""           # URL or source name for attribution
    error: str = ""            # Human-readable error if success=False


@dataclass
class CircuitBreaker:
    """
    Prevents hammering a failing external service.

    State machine:
      CLOSED (normal) → too many failures → OPEN (blocked)
      OPEN → recovery time passes → CLOSED again

    Example: Tavily fails 3 times → circuit opens → skip Tavily for 5 min.
    """
    name: str
    threshold: int = settings.cb_fail_threshold    # failures before opening
    recovery_s: int = settings.cb_recovery_s       # seconds before auto-close
    failures: int = field(default=0, init=False)
    open_until: datetime | None = field(default=None, init=False)

    def is_open(self) -> bool:
        """Returns True if circuit is open (service is blocked)."""
        if self.open_until is None:
            return False
        if datetime.now() < self.open_until:
            return True
        # Recovery time has passed — reset and close
        self.failures = 0
        self.open_until = None
        logger.info("circuit_breaker_recovered", service=self.name)
        return False

    def record_failure(self) -> None:
        """Record a failure. Opens circuit if threshold is reached."""
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_until = datetime.now() + timedelta(seconds=self.recovery_s)
            logger.warning(
                "circuit_breaker_open",
                service=self.name,
                failures=self.failures,
                recovery_s=self.recovery_s,
            )

    def record_success(self) -> None:
        """Reset failure count on a successful call."""
        self.failures = 0


def with_retry(max_attempts: int = 3, backoff: float = 1.5):
    """
    Decorator: retries an async function with exponential backoff.

    Attempt 1 fails → wait 1.5s → attempt 2
    Attempt 2 fails → wait 2.25s → attempt 3
    Attempt 3 fails → raise the exception

    Usage:
        @with_retry(max_attempts=3, backoff=1.5)
        async def my_tool(...):
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        wait = backoff ** (attempt - 1)
                        logger.warning(
                            "tool_retry",
                            tool=fn.__name__,
                            attempt=attempt,
                            wait_s=round(wait, 2),
                            error=str(e)[:100],
                        )
                        await asyncio.sleep(wait)
            raise last_error
        return wrapper
    return decorator
