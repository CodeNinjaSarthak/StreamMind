# Frontend Components

> Purpose: Every component — what it renders, what data/WS events it consumes, and critical quirks.

<!-- Populate from: frontend/src/components/, frontend/src/pages/ -->

## Pages

### LandingPage
`frontend/src/pages/LandingPage.jsx`
- **Renders:** Dark-themed landing page with orange accent (#FF6B35). Header with logo + nav, hero section with tagline and CTA buttons, "How It Works" section with 3 numbered feature cards (Connect, AI Processes, Review & Post), footer with tech attribution
- **Fonts:** Azeret Mono (display), Outfit (body)
- **Animations:** CSS entrance animations (anim-nav, anim-1 through anim-4)
- **Behavior:** Redirects authenticated users to `/dashboard`
- **Data:** None (static content)

### LoginPage
`frontend/src/pages/LoginPage.jsx`
- **Renders:** Login form
- **Data:** `AuthContext.login()`

### RegisterPage
`frontend/src/pages/RegisterPage.jsx`
- **Renders:** Registration form
- **Data:** `AuthContext.register()`

### DashboardPage
`frontend/src/pages/DashboardPage.jsx`
- **Renders:** Full teacher dashboard; composes all dashboard sub-components
- **Data:** Session list, WebSocket connection
- **Notes:** <!-- any page-level state management notes -->

### SettingsPage
`frontend/src/pages/SettingsPage.jsx`
- **Renders:** Profile settings, password change
- **Data:** `updateProfile()`, `changePassword()` from API service

---

## Dashboard Components

### SessionList
`frontend/src/components/Dashboard/SessionList.jsx`
- **Renders:** List of teacher's sessions with "Switch Session" button
- **Data:** `GET /api/v1/sessions`
- **Critical quirks:** <!-- any known issues or non-obvious behavior -->

### YouTubePanel
`frontend/src/components/Dashboard/YouTubePanel.jsx`
- **Renders:** YouTube connection status, OAuth connect button, video ID input
- **Data:** YouTube auth status, OAuth URL
- **Events:** Opens OAuth popup; listens for `postMessage` from callback

### ManualInput
`frontend/src/components/Dashboard/ManualInput.jsx`
- **Renders:** Text input for manually submitting a question
- **Data:** `submitManualQuestion()` → `POST /api/v1/dashboard/sessions/{id}/manual-question`
- **Limits:** Max 10 questions per submission (one per line), text 1-5000 chars
- **Critical quirks:** Uses dashboard route, not a generic comments route

### MetricsCards
`frontend/src/components/Dashboard/MetricsCards.jsx`
- **Renders:** Stats cards (total questions, clusters, answers, posted)
- **Data:** `GET /api/v1/dashboard/sessions/{session_id}/stats`
- **Critical quirks:** Uses per-session stats endpoint, NOT a global metrics endpoint

### QuestionsFeed
`frontend/src/components/Dashboard/QuestionsFeed.jsx`
- **Renders:** Real-time feed of classified questions
- **Data:** Initial load + `comment_created`, `comment_classified` WS events
- **Events:** `comment_created`, `comment_classified`

### ClustersPanel
`frontend/src/components/Dashboard/ClustersPanel.jsx`
- **Renders:** Clusters with associated questions and generated answers
- **Data:** `cluster_created`, `cluster_updated`, `answer_ready` WS events
- **Events:** `cluster_created`, `cluster_updated`, `answer_ready`, `answer_posted`

### ActivityLog
`frontend/src/components/Dashboard/ActivityLog.jsx`
- **Renders:** Chronological feed of the last 20 events (newest first), each with emoji icon, label, and relative timestamp
- **Event types:** comment_created, comment_classified, cluster_created, cluster_updated, answer_ready, answer_posted, session_started, session_ended, quota_alert, quota_exceeded
- **Data:** WebSocket messages from `useWebSocket` hook

### AnalyticsPanel
`frontend/src/components/Dashboard/AnalyticsPanel.jsx`
- **Renders:** Stats grid (total questions, clusters answered %, avg cluster size, peak hour), cumulative line chart (Questions Over Time via Recharts), hourly bar chart, top topics ranked list, export buttons (CSV and JSON)
- **Data:** `GET /api/v1/sessions/{id}/analytics` — debounced refetch on WebSocket events (2000ms)
- **Export:** CSV (Questions, Answers, Cluster, Timestamp, Is Posted) and JSON (detailed cluster objects)

### DocumentUpload
`frontend/src/components/Dashboard/DocumentUpload.jsx`
- **Renders:** Collapsible section with file input (.pdf, .docx, .txt, max 10MB), upload progress bar, list of uploaded documents with delete buttons
- **Data:** `POST /api/v1/rag/documents` (XHR-based with progress), `GET /api/v1/rag/documents`, `DELETE /api/v1/rag/documents/{id}`

### QuotaBanner
`frontend/src/components/Dashboard/QuotaBanner.jsx`
- **Renders:** Alert bar at top of dashboard when YouTube quota is running low (warning) or exhausted (critical). Dismissible.
- **Data:** `quota_alert` and `quota_exceeded` WebSocket events

### ClusterDetailsModal
`frontend/src/components/Dashboard/ClusterDetailsModal.jsx`
- **Renders:** Modal overlay showing cluster title, all comments in the cluster, and generated answer. Click outside closes.
- **Data:** `GET /api/v1/clusters/{id}/comments`

### KeyboardShortcutsModal
`frontend/src/components/Dashboard/KeyboardShortcutsModal.jsx`
- **Renders:** Modal with table of keyboard shortcuts (? = help, N = new session, A = approve first pending, Ctrl+K = focus input, Esc = close)
- **Data:** None (static content)

---

## Auth / Layout Components

### Header
`frontend/src/components/Layout/Header.jsx`
- **Renders:** Logo, active session name with "LIVE" badge, connection status dot (connected/connecting/reconnecting), user name, theme toggle, Settings link, Logout button

### ProtectedRoute
`frontend/src/components/Layout/ProtectedRoute.jsx`
- **Renders:** Wraps children; redirects to `/login` if not authenticated

### LoginForm / RegisterForm
`frontend/src/components/Auth/LoginForm.jsx`, `RegisterForm.jsx`
- **Renders:** Email + password form (RegisterForm adds name field), error display, loading state, link to alternate auth page

### ErrorBoundary
`frontend/src/components/ErrorBoundary.jsx`
- **Renders:** Catches React render errors, shows error details + Retry button (reloads page)

### GlobalShortcutsHandler
`frontend/src/components/GlobalShortcutsHandler.jsx`
- **Renders:** Invisible — listens for `?` (show shortcuts modal) and `Esc` (close modal). Only active when authenticated.

---

## WebSocket Event → Component Mapping

| Event | Consumed by |
|-------|-------------|
| `comment_created` | QuestionsFeed, MetricsCards, ActivityLog |
| `comment_classified` | QuestionsFeed, MetricsCards, ActivityLog |
| `cluster_created` | ClustersPanel, MetricsCards, ActivityLog |
| `cluster_updated` | ClustersPanel, ActivityLog |
| `answer_ready` | ClustersPanel, MetricsCards, ActivityLog |
| `answer_posted` | ClustersPanel, MetricsCards, ActivityLog |
| `quota_alert` | QuotaBanner, ActivityLog |
| `quota_exceeded` | QuotaBanner, ActivityLog |

For full event payload shapes, see [api/websocket-events.md](../api/websocket-events.md).
