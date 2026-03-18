# YouTube OAuth

> Purpose: Full OAuth flow, CSRF state tokens in Redis, popup postMessage pattern, HTTPS requirement.

<!-- Populate from: backend/app/services/youtube/oauth.py, backend/app/api/v1/youtube.py, docs/_archive/YOUTUBE_SETUP.md -->

## Overview

YouTube OAuth uses a popup-window pattern so teachers can authorize without leaving
the dashboard. The flow uses CSRF state tokens stored in Redis to prevent forgery.

## Prerequisites (Google Cloud Setup)

See [`_archive/YOUTUBE_SETUP.md`](../_archive/YOUTUBE_SETUP.md) for the full Google Cloud
Console setup guide (create project, enable API, configure OAuth consent screen, create credentials).

## OAuth Flow

```
Teacher (Dashboard)                Backend                        Google OAuth
        │                              │                               │
        │─── GET /api/v1/youtube/auth/url ──►                          │
        │                              │── generate state (UUID)       │
        │                              │── Redis SET yt_state:{state}  │
        │                              │      (TTL 10 minutes)         │
        │◄─── { url, state } ──────────│                               │
        │                              │                               │
        │── window.open(url) ─────────────────────────────────────────►│
        │                              │                               │
        │                              │◄─── redirect to callback ─────│
        │                              │    with ?code=...&state=...   │
        │                              │                               │
        │                              │── validate state token:       │
        │                              │   GET Redis yt_state:{state}  │
        │                              │   (must exist and match)      │
        │                              │                               │
        │                              │── exchange code for tokens    │
        │                              │── encrypt + store in DB       │
        │                              │── DELETE Redis yt_state:{...} │
        │                              │                               │
        │◄─── HTML with postMessage ───│                               │
        │   ({"type":"youtube_auth_success"})                          │
        │                              │                               │
        │── window.addEventListener("message") closes popup            │
```

## CSRF State Tokens

Redis key pattern: `yt_state:{state_uuid}`
Also stored per-teacher: `yt_state_teacher:{teacher_id}` → state_uuid

- TTL: 10 minutes
- Purpose: prevent CSRF attacks on the OAuth callback
- The callback rejects any `state` not found in Redis

## Callback Response

`GET /api/v1/youtube/auth/callback` returns an HTML page that:
1. Calls `window.opener.postMessage({type: "youtube_auth_success"}, origin)`
2. Calls `window.close()`

The dashboard listens for this message to update YouTube connection status.

## Token Storage

YouTube access and refresh tokens are:
1. Encrypted via `encrypt_data` (`backend/app/core/encryption.py`) using Fernet symmetric encryption
2. Stored in the `YouTubeToken` model (one per teacher, `teacher_id` UNIQUE constraint)
3. Fields: `access_token`, `refresh_token`, `token_type`, `scope`, `expires_at`

See [security/secrets-management.md](secrets-management.md) for encryption details.
See [data/schema.md](../data/schema.md) for the YouTubeToken model definition.

## HTTPS Requirement

Google's OAuth requires the redirect URI to be HTTPS in production.
- Development: `http://localhost:8000/api/v1/youtube/auth/callback` is allowed
- Production: must be `https://your-domain.com/api/v1/youtube/auth/callback`

Update `YOUTUBE_REDIRECT_URI` env var and the Google Cloud Console allowed redirect URIs.
See [infra/deployment.md](../infra/deployment.md).

## Token Refresh

`POST /api/v1/youtube/auth/refresh` — exchanges the stored refresh token for a new
access token using the OAuth client credentials.

## Troubleshooting

See [state/runbooks/youtube-quota-exceeded.md](../state/runbooks/youtube-quota-exceeded.md)
for quota-related issues.
