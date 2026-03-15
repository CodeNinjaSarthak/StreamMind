"""Circuit breaker for Gemini API calls."""

import logging
import time

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open — Gemini calls blocked."""

    pass


class GeminiCircuitBreaker:
    """Per-process circuit breaker that fails fast during sustained Gemini outages."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        state_change_callback: callable | None = None,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = "closed"
        self._opened_at = None
        self._state_change_callback = state_change_callback

    @property
    def state(self) -> str:
        """Returns 'closed', 'open', or 'half_open'."""
        if self._state == "open" and time.monotonic() - self._opened_at >= self._recovery_timeout:
            return "half_open"
        return self._state

    def record_success(self) -> None:
        """Reset failure count, close circuit."""
        was_open = self._state != "closed"
        self._failure_count = 0
        self._state = "closed"
        self._opened_at = None
        if was_open:
            logger.info("Gemini circuit breaker closed after successful probe")
            if self._state_change_callback:
                self._state_change_callback(self.state)

    def record_failure(self) -> None:
        """Increment failure count. Open circuit if threshold reached."""
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold and self._state == "closed":
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.warning(
                "Gemini circuit breaker OPEN after %d consecutive failures. " "Calls blocked for %.0fs.",
                self._failure_count,
                self._recovery_timeout,
            )
            if self._state_change_callback:
                self._state_change_callback(self.state)

    def ensure_closed(self) -> None:
        """Raise CircuitOpenError if circuit is open. Allow if half_open or closed."""
        current = self.state
        if current == "open":
            raise CircuitOpenError(f"Gemini circuit breaker is open. Retry after {self._recovery_timeout}s.")
        if current == "half_open":
            logger.info("Gemini circuit breaker half-open, allowing probe request")
