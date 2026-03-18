# Frontend Overview

> Purpose: React 19 + Vite 7, routing, AuthProvider, Vite proxy config, dev/build setup.

<!-- Populate from: frontend/src/main.jsx, frontend/src/App.jsx, frontend/vite.config.js -->

## Stack

- **Framework:** React 19
- **Build tool:** Vite 7
- **Dev server:** `http://localhost:5173`
- **Production:** Built to `frontend/dist/`; served by FastAPI StaticFiles when `FRONTEND_DIR` is set

See [ADR-005](../architecture/decisions/ADR-005-react-vite-frontend.md) for rationale.

## Entry Points

```
frontend/src/main.jsx   → renders <BrowserRouter><App /></BrowserRouter>
frontend/src/App.jsx    → AuthProvider, route definitions
```

## Routes

| Path | Component | Auth required |
|------|-----------|--------------|
| `/` | LandingPage | No |
| `/login` | LoginPage | No (redirects if logged in) |
| `/register` | RegisterPage | No (redirects if logged in) |
| `/dashboard` | DashboardPage | Yes |
| `/settings` | SettingsPage | Yes |

<!-- Populate additional routes if any -->

## AuthProvider

`frontend/src/context/AuthContext.jsx`

Provides:
- `user` — current user object or null
- `token` — JWT access token string
- `login(email, password)` — calls API, stores tokens
- `logout()` — clears tokens, calls logout API
- `refreshToken()` — auto-refreshes on 401

Token storage: `localStorage` — keys `token` and `refreshToken`. Required for WebSocket auth (first-message JWT pattern).

Hook: `useAuth()` from `frontend/src/hooks/useAuth.js`

See [frontend/state-and-hooks.md](state-and-hooks.md) for hook contracts.

## Vite Proxy

`frontend/vite.config.js` proxies during development:

| Prefix | Target | Notes |
|--------|--------|-------|
| `/api` | `http://localhost:8000` | REST API |
| `/ws` | `ws://localhost:8000` | WebSocket upgrade |

## CORS

`http://localhost:5173` is included in `backend/.env.development` `CORS_ORIGINS`.
See [infra/configuration-reference.md](../infra/configuration-reference.md).

## Build

```bash
cd frontend
npm install
npm run dev      # Dev server at :5173
npm run build    # Output to frontend/dist/
```

Set `FRONTEND_DIR=frontend/dist` in backend env for production StaticFiles serving.
