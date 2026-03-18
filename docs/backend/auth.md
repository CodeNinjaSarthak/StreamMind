# Authentication

> Purpose: JWT lifecycle, bcrypt hashing, HTTPBearer scheme, token blacklist, and refresh endpoint.

<!-- Populate from: backend/app/core/security.py, backend/app/api/v1/auth.py -->

## JWT Configuration

| Parameter | Value | Config key |
|-----------|-------|-----------|
| Access token TTL | 30 minutes | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh token TTL | 7 days | `REFRESH_TOKEN_EXPIRE_DAYS` |
| Algorithm | HS256 | `ALGORITHM` |
| Secret key | Random 32-byte hex | `SECRET_KEY` |

How to generate SECRET_KEY: see [backend/configuration.md](configuration.md).

## Password Hashing

bcrypt with cost factor 12 (`bcrypt_rounds = 12`).

## HTTPBearer Scheme

All protected endpoints use `Depends(get_current_active_user)`, which:
1. Extracts Bearer token from `Authorization` header
2. Decodes and validates JWT signature + expiry
3. Checks token blacklist (Redis key `blacklist:token:{hash}`)
4. Loads user from DB; verifies `is_active=True`
5. Returns `User` model or raises `401 Unauthorized`

## Token Blacklist

On logout, the token's `jti` claim is written to Redis with TTL matching the remaining
token lifetime. This ensures invalidated tokens cannot be reused even before expiry.

Redis key pattern: `blacklist:token:{hash}`

## Refresh Flow

```
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
→ new access_token (30min) + new refresh_token (7d)
```

Old refresh token is blacklisted on use (rotation).

## Error Responses

See [api/error-codes.md](../api/error-codes.md) for 401/403 response shapes.
