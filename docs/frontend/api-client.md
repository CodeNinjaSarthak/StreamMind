# Frontend API Client

> Purpose: apiFetch helper, all named service exports, token injection, and critical quirks.

<!-- Populate from: frontend/src/services/api.js -->
<!-- REST endpoint specs live in api/rest.md — do NOT duplicate schemas here -->

## apiFetch Helper

`frontend/src/services/api.js` — internal `apiFetch(path, options)` function

- Prepends `/api/v1` to all paths
- Injects `Authorization: Bearer {token}` header from AuthContext
- On 401: calls `refreshToken()` once, retries, then calls `logout()`
- Throws on non-2xx responses with parsed error body

## Named Service Exports

| Export | Method + Path | Critical Notes |
|--------|--------------|---------------|
| `login(email, password)` | `POST /api/v1/auth/login` | |
| `register(data)` | `POST /api/v1/auth/register` | |
| `logout()` | `POST /api/v1/auth/logout` | |
| `refreshAuthToken()` | `POST /api/v1/auth/refresh` | |
| `getSessions()` | `GET /api/v1/sessions` | |
| `createSession(data)` | `POST /api/v1/sessions` | |
| `getSession(id)` | `GET /api/v1/sessions/{id}` | |
| `getSessionStats(id)` | `GET /api/v1/dashboard/sessions/{id}/stats` | Returns stats object |
| `submitManualQuestion(sessionId, text)` | `POST /api/v1/dashboard/sessions/{id}/manual-question` | Uses dashboard route; max 10 questions per line |
| `approveAnswer(answerId)` | `POST /api/v1/dashboard/answers/{id}/approve` | **Takes answerId, NOT clusterId** |
| `editAnswer(answerId, text)` | `PATCH /api/v1/dashboard/answers/{id}` | |
| `getYouTubeAuthUrl()` | `GET /api/v1/youtube/auth/url` | |
| `getYouTubeAuthStatus()` | `GET /api/v1/youtube/auth/status` | |
| `disconnectYouTube()` | `DELETE /api/v1/youtube/auth/disconnect` | |
| `validateYouTubeVideo(videoId)` | `GET /api/v1/youtube/videos/{id}/validate` | |
| `uploadDocument(sessionId, file, token, onProgress)` | `POST /api/v1/rag/documents` | XHR-based with progress callback; multipart/form-data |
| `getDocuments({token, sessionId?})` | `GET /api/v1/rag/documents` | |
| `deleteDocument(documentId, token)` | `DELETE /api/v1/rag/documents/{id}` | |
| `updateProfile(data, token)` | `PATCH /api/v1/auth/profile` | |
| `changePassword(currentPassword, newPassword, token)` | `POST /api/v1/auth/change-password` | |
| `getSessionComments(sessionId, token, limit, offset)` | `GET /api/v1/sessions/{id}/comments?limit=&offset=` | Paginated; default limit=100 |
| `getSessionClusters(sessionId, token)` | `GET /api/v1/sessions/{id}/clusters` | |
| `getSessionAnalytics(sessionId, token)` | `GET /api/v1/sessions/{id}/analytics` | |
| `endSession(id, token)` | `POST /api/v1/sessions/{id}/end` | |
| `getClusterComments(clusterId, token)` | `GET /api/v1/clusters/{id}/comments` | |
| `getRepresentativeQuestion(clusterId, token)` | `GET /api/v1/dashboard/clusters/{id}/representative` | |
| `refreshAccessToken()` | `POST /api/v1/auth/refresh` | Deduped via refreshPromise |

## Critical Quirks

- `approveAnswer(answerId)` — takes `answer_id`, **not** `cluster_id`. This is a common
  mistake. The answer ID is found in the `answer_ready` WebSocket event's `data.answer_id`.
- `submitManualQuestion` — uses the dashboard route (`/api/v1/dashboard/sessions/{id}/manual-question`),
  not a generic comments endpoint.
- Token injection — `token` must be in the `useAuth` dependency array of any `useEffect`
  that calls API functions, or the stale closure will use the old token.

## Full Endpoint Specs

For request/response schemas, see [api/rest.md](../api/rest.md).
This file documents the JavaScript wrapper layer, not the HTTP contract.
