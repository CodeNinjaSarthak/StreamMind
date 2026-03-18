"""End-to-end tests for Phase 2.5 tech debt fixes."""

import os
import sys
import time

import requests

BASE_URL = "http://localhost:8000"
TEST_EMAIL = f"techdebt_{int(time.time())}@test.com"
TEST_PASSWORD = "TestPass123!"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

failures = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  [{PASS}] {label}")
    else:
        print(f"  [{FAIL}] {label}" + (f" — {detail}" if detail else ""))
        failures.append(label)


def clear_rate_limits():
    """Clear rate limit keys from Redis to avoid test pollution."""
    try:
        import redis

        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        deleted = 0
        for key in r.scan_iter("ratelimit:*"):
            r.delete(key)
            deleted += 1
        if deleted > 0:
            print(f"\n🧹 Cleared {deleted} rate limit key(s) from Redis")
    except Exception as e:
        print(f"\n⚠️  Could not clear rate limits: {e}")


# ---------------------------------------------------------------------------
# Test 1: Rate Limiting
# ---------------------------------------------------------------------------
print("\n=== Test 1: Rate Limiting ===")
responses = [requests.get(f"{BASE_URL}/api/v1/sessions/") for _ in range(70)]
statuses = [r.status_code for r in responses]
count_429 = statuses.count(429)
count_200_401 = sum(1 for s in statuses if s in (200, 401, 403))
check(
    "Some requests are rate-limited (429)",
    count_429 > 0,
    f"got {count_429} 429s out of 70 requests",
)
check(
    "All requests accounted for (200/401/403 + 429 == 70)",
    count_200_401 + count_429 == 70,
    f"200/401/403={count_200_401}, 429={count_429}",
)
if count_429 > 0:
    rate_limited_resp = next(r for r in responses if r.status_code == 429)
    check(
        "429 response has Retry-After header",
        "Retry-After" in rate_limited_resp.headers,
    )

# CLEAR RATE LIMITS BEFORE NEXT TESTS
clear_rate_limits()
time.sleep(1)  # Let Redis settle

# ---------------------------------------------------------------------------
# Test 2: Encryption roundtrip (no fixed_salt)
# ---------------------------------------------------------------------------
print("\n=== Test 2: Encryption ===")
try:
    import subprocess

    # Check source for fixed_salt
    result = subprocess.run(
        ["grep", "-r", "fixed_salt", os.path.join(os.path.dirname(__file__), "../backend")],
        capture_output=True,
        text=True,
    )
    check(
        "No hardcoded fixed_salt in source",
        result.returncode != 0,
        f"found: {result.stdout.strip()}" if result.returncode == 0 else "",
    )

    # Test roundtrip via direct import
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))
    from app.core.encryption import (
        decrypt_data,
        encrypt_data,
    )

    plaintext = "hello world secret"
    encrypted = encrypt_data(plaintext)
    decrypted = decrypt_data(encrypted)
    check("Encrypt/decrypt roundtrip succeeds", decrypted == plaintext, f"got: {decrypted!r}")
    check("Encrypted != plaintext", encrypted != plaintext)
except Exception as e:
    check("Encryption import/roundtrip", False, str(e))

# ---------------------------------------------------------------------------
# Test 3: Auth-gated /api/v1/metrics endpoint
# ---------------------------------------------------------------------------
print("\n=== Test 3: Metrics Endpoint ===")

# Register
reg = requests.post(
    f"{BASE_URL}/api/v1/auth/register",
    json={"email": TEST_EMAIL, "name": "Tech Debt Tester", "password": TEST_PASSWORD},
)
check("Register succeeds", reg.status_code == 201, f"status={reg.status_code}")

# Login
login = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
check("Login succeeds", login.status_code == 200, f"status={login.status_code}")
token = login.json().get("access_token", "") if login.status_code == 200 else ""

# Unauthenticated request should be 401 or 403
unauth = requests.get(f"{BASE_URL}/api/v1/metrics")
check(
    "GET /api/v1/metrics without token → 401/403",
    unauth.status_code in (401, 403),
    f"status={unauth.status_code}",
)

if token:
    metrics_resp = requests.get(f"{BASE_URL}/api/v1/metrics", headers={"Authorization": f"Bearer {token}"})
    check(
        "GET /api/v1/metrics with token → 200",
        metrics_resp.status_code == 200,
        f"status={metrics_resp.status_code}",
    )
    if metrics_resp.status_code == 200:
        body = metrics_resp.json()
        expected_keys = {"active_sessions", "questions_processed", "answers_generated"}
        check(
            "Metrics response has all expected keys",
            expected_keys.issubset(body.keys()),
            f"got keys: {set(body.keys())}",
        )

# ---------------------------------------------------------------------------
# Test 4: Token Blacklist (logout invalidates token)
# ---------------------------------------------------------------------------
print("\n=== Test 4: Token Blacklist ===")

# Fresh login for a clean token
login2 = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
check("Second login succeeds", login2.status_code == 200, f"status={login2.status_code}")
token2 = login2.json().get("access_token", "") if login2.status_code == 200 else ""

if token2:
    # Verify token works pre-logout
    me_before = requests.get(f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    check("Token valid before logout", me_before.status_code == 200, f"status={me_before.status_code}")

    # Logout
    logout_resp = requests.post(f"{BASE_URL}/api/v1/auth/logout", headers={"Authorization": f"Bearer {token2}"})
    check("Logout succeeds", logout_resp.status_code == 200, f"status={logout_resp.status_code}")

    # Old token should now be rejected
    me_after = requests.get(f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    check(
        "Old token rejected after logout (401/403)",
        me_after.status_code in (401, 403),
        f"status={me_after.status_code}",
    )

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'=' * 40}")
if failures:
    print(f"FAILED ({len(failures)} test(s)):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("All tests passed!")
    sys.exit(0)
