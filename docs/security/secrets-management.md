# Secrets Management

> Purpose: What is secret, encrypt_data/decrypt_data usage, token rotation, and .gitignore rules.

<!-- Populate from: backend/app/core/encryption.py, backend/.env.example -->

## What Is Secret

| Secret | Where used | Rotation procedure |
|--------|-----------|-------------------|
| `SECRET_KEY` | JWT signing | Generate new value → update env → restart backend → all existing tokens invalidated |
| `GEMINI_API_KEY` | Gemini API calls | Revoke in Google AI Studio → generate new → update env |
| `YOUTUBE_CLIENT_ID` / `CLIENT_SECRET` | YouTube OAuth | Revoke in Google Cloud Console → update env → re-authorize teachers |
| `ENCRYPTION_KEY` | OAuth token encryption in DB | See rotation procedure below |
| `DATABASE_URL` | DB connection (contains password) | Change DB password → update env |

## encrypt_data / decrypt_data

`backend/app/core/encryption.py`

Used to encrypt sensitive values before storing in PostgreSQL:
- `YouTubeToken.access_token`
- `YouTubeToken.refresh_token`

```python
from backend.app.core.encryption import encrypt_data, decrypt_data

encrypted = encrypt_data(plaintext_token)   # stores in DB
decrypted = decrypt_data(encrypted_token)   # retrieved from DB for API calls
```

Algorithm: Fernet (symmetric encryption via `cryptography.fernet.Fernet`)
Key derivation: First 32 bytes of `ENCRYPTION_KEY` env var, base64-encoded for Fernet. Config validator ensures key is ≥32 characters.

## Rotating ENCRYPTION_KEY

If the encryption key must be rotated:
1. Generate new key
2. For each `YouTubeToken` with stored tokens:
   - Decrypt with old key
   - Re-encrypt with new key
   - Save
3. Update `ENCRYPTION_KEY` env var
4. Restart backend

> This must be done atomically. Running with mismatched keys will cause token decryption failures.

## .gitignore Rules

The following must never be committed:

```
backend/.env
backend/.env.development
backend/.env.production
*.env
*.env.*
```

Verify with: `git status` and `git diff --cached` before committing.

## Environment Variable Handling

- Use `.env.example` files with placeholder values as templates
- Actual `.env.*` files are in `.gitignore`
- In CI/CD: inject secrets via environment variables or secrets manager (not files)

For the full list of secret env vars, see [infra/configuration-reference.md](../infra/configuration-reference.md).
