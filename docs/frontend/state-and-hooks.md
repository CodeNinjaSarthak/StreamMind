# State and Hooks

> Purpose: Hook contracts — useWebSocket (backoff + 100-msg cap), useAuth context values, and other hooks.

<!-- Populate from: frontend/src/hooks/, frontend/src/context/ -->

## useAuth

`frontend/src/hooks/useAuth.js` — consumes `AuthContext`

### Contract

```js
const {
  token,          // string | null — JWT access token
  displayName,    // string | null — user's display name
  userEmail,      // string | null
  userName,       // string | null
  isAuthenticated,// bool
  login,          // async (email, password) → void (throws on error)
  logout,         // async () → void
  register,       // async (email, password, name) → void
  updateProfile,  // async (name) → void
} = useAuth()
```

### Usage

Must be used inside `<AuthProvider>`. Throws if called outside context.

---

## useWebSocket

`frontend/src/hooks/useWebSocket.js`

### Contract

```js
const {
  messages,       // array — last 100 events (capped, oldest dropped)
  connected,      // bool
  reconnecting,   // bool — true during reconnection attempts
} = useWebSocket(sessionId, token)
```

### Behavior

- **Reconnection:** Exponential backoff on disconnect
  - Initial delay: 1000ms
  - Max delay: 30000ms (capped)
  - Formula: `Math.min(1000 * 2^retry_count, 30000)`
  - Gives up after: 10 retries (MAX_RETRIES=10)
  - Auth failures (4001, 4003) do NOT retry
- **Message cap:** Caps at 100 messages (oldest dropped on overflow)
  - Prevents memory growth during long sessions
- **Auth:** Sends `{"type": "auth", "token": "<jwt>"}` as first message after connection opens
- **Cleanup:** Closes connection on component unmount or sessionId change

### Event Handling

Each incoming message is JSON-parsed and pushed to `messages`. Components subscribe
to `lastEvent` or filter `messages` by `type`.

---

## useToast

`frontend/src/hooks/useToast.js`

### Contract

```js
import { showToast } from '../hooks/useToast'

showToast('Operation succeeded', 'success')  // types: 'info' | 'error' | 'success'
```

Global function — can be called from anywhere (no Provider needed). `ToastContainer` subscribes on mount. Auto-dismisses after 4000ms.

---

## useKeyboardShortcuts

`frontend/src/hooks/useKeyboardShortcuts.js`

### Contract

```js
useKeyboardShortcuts({
  onNewSession,   // called on 'N' key
  onApproveFirst, // called on 'A' key
  onFocusSearch,  // called on Ctrl+K / Cmd+K
  enabled: true,  // disable when modal open, etc.
})
```

Ignores shortcuts when active element is INPUT, TEXTAREA, SELECT, or contentEditable. `Ctrl+K` / `Cmd+K` works even while typing (preventDefault).

---

## AuthContext

`frontend/src/context/AuthContext.jsx`

Manages token storage and auto-refresh.

- **Storage:** `localStorage` keys: `token`, `refreshToken`
- **Auto-refresh:** On mount, checks stored token expiry (JWT decode). If expired, attempts refresh using stored refresh token. If refresh fails, logs out and redirects to `/login`.
- **Cross-tab:** ThemeContext (separate) syncs dark/light mode across tabs via `storage` events.
