# Chrome Extension Overview

> Purpose: Manifest V3 permissions, background Service Worker lifecycle, alarms keep-alive, and content script.

> **Status:** Fully functional. Not yet published to the Chrome Web Store — currently in testing via "Load unpacked" in developer mode.

<!-- Populate from: chrome-extension/ directory (verify path) -->

## Stack

- Manifest Version: 3
- Build: TypeScript → `npm run build`
- Background: Service Worker (`background/index.ts`)

## Manifest Permissions

<!-- List required permissions and their justification -->

```json
{
  "permissions": [
    "storage",
    "alarms",
    "identity"
  ],
  "host_permissions": [
    "https://www.youtube.com/*",
    "https://your-backend-domain.com/*"
  ]
}
```

## Service Worker Lifecycle

Chrome MV3 Service Workers sleep after ~5 minutes of inactivity. To keep the
background alive during active YouTube sessions:

- **Chrome Alarms API:** Periodic alarm fires every <!-- N --> minutes, waking the SW
- Alarm name: <!-- document the alarm name -->

## Background Services

Five modules compose the background service. See [chrome-extension/background-services.md](background-services.md) for details:

- `auth.ts` — OAuth token management
- `youtubePoller.ts` — YouTube chat polling
- `websocket.ts` — Backend WebSocket connection
- `quota.ts` — Client-side quota tracking
- `index.ts` — Entry point, wires modules together

## Content Script

<!-- What pages does the content script run on? What does it inject/extract? -->

## Communication

| Channel | Purpose |
|---------|---------|
| `chrome.runtime.sendMessage` | Content script → background |
| `chrome.storage.local` | Persistent state (tokens, session info) |
| Backend WebSocket | Real-time events from backend |
