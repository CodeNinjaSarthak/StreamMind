# Chrome Extension Build and Load

> Purpose: Build steps, load unpacked, dev vs prod backend URL configuration.

> **Status:** The extension is fully working and can be loaded unpacked for development and testing. It is not yet published to the Chrome Web Store.

<!-- Populate from: chrome-extension/package.json, README (if exists) -->

## Build

```bash
cd chrome-extension   # verify path
npm install
npm run build         # outputs to dist/ or build/ (verify)
```

## Load Unpacked (Development)

1. Open Chrome → `chrome://extensions`
2. Enable "Developer mode" (top right toggle)
3. Click "Load unpacked"
4. Select the `dist/` (or `build/`) output directory

## Dev vs Prod Backend URL

The extension must point to the correct backend URL.

| Environment | Backend URL |
|-------------|-------------|
| Development | `http://localhost:8000` |
| Production | `https://your-domain.com` |

Configuration location: <!-- environment config file or build-time variable -->

```bash
# Example: build for production
BACKEND_URL=https://your-domain.com npm run build
```

## Reloading Changes

After rebuilding:
1. Go to `chrome://extensions`
2. Click the refresh icon on your extension card
3. Reload any YouTube tab that has the content script injected

## Permissions Note

On first install, Chrome will ask the user to approve the extension's permissions.
If permissions change in `manifest.json`, the extension may be disabled until the
user re-approves.
