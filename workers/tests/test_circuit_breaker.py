"""Contract tests for GeminiCircuitBreaker.

Tests assert ONLY on observable behavior (ensure_closed raises or not,
callback values received). Never asserts on _state, _failure_count, or
any private attribute.
"""

import pytest
from app.services.gemini.circuit_breaker import (
    CircuitOpenError,
    GeminiCircuitBreaker,
)


def test_calls_succeed_when_healthy():
    """Circuit allows calls when no failures recorded."""
    cb = GeminiCircuitBreaker(failure_threshold=3)
    cb.ensure_closed()  # must not raise


def test_blocks_calls_after_sustained_failures():
    """Circuit rejects calls after hitting failure threshold."""
    cb = GeminiCircuitBreaker(failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.ensure_closed()


def test_recovers_after_cooldown(monkeypatch):
    """Circuit allows probe attempt after recovery timeout."""
    cb = GeminiCircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    for _ in range(3):
        cb.record_failure()
    # Fast-forward past recovery_timeout
    monkeypatch.setattr("app.services.gemini.circuit_breaker.time.monotonic", lambda: 1_000_000.0 + 31.0)
    cb.ensure_closed()  # half_open allows probe — must not raise


def test_successful_probe_closes_circuit(monkeypatch):
    """Successful probe after cooldown fully closes the circuit."""
    cb = GeminiCircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    for _ in range(3):
        cb.record_failure()
    monkeypatch.setattr("app.services.gemini.circuit_breaker.time.monotonic", lambda: 1_000_000.0 + 31.0)
    cb.ensure_closed()  # probe attempt
    cb.record_success()  # probe succeeded
    # Circuit is now closed — next call must succeed
    cb.ensure_closed()


def test_failed_probe_reopens_circuit(monkeypatch):
    """Failed probe restarts cooldown — circuit stays closed to calls."""
    base_time = 1_000_000.0
    current_time = [base_time]
    monkeypatch.setattr("app.services.gemini.circuit_breaker.time.monotonic", lambda: current_time[0])

    cb = GeminiCircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    for _ in range(3):
        cb.record_failure()

    # Advance past recovery timeout — enters half_open
    current_time[0] = base_time + 31.0
    cb.ensure_closed()  # probe attempt — half_open allows it
    cb.record_failure()  # probe failed — must restart cooldown

    # Time hasn't advanced further — circuit should block again
    with pytest.raises(CircuitOpenError):
        cb.ensure_closed()


def test_callback_fires_on_state_changes():
    """Callback receives open and closed signals on transitions."""
    STATE_MAP = {"closed": 0, "half_open": 1, "open": 2}
    received = []
    cb = GeminiCircuitBreaker(
        failure_threshold=3,
        state_change_callback=lambda s: received.append(STATE_MAP[s]),
    )
    # Drive to open
    for _ in range(3):
        cb.record_failure()
    # Drive to closed
    cb.record_success()

    assert len(received) == 2
    assert received[0] == STATE_MAP["open"]
    assert received[1] == STATE_MAP["closed"]
