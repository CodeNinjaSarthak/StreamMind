# YouTube API Setup Guide

## Prerequisites

- Google account with access to [Google Cloud Console](https://console.cloud.google.com)
- A YouTube account that can create live streams

---

## Step 1: Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Name it (e.g., "StreamMind") and click **Create**

---

## Step 2: Enable YouTube Data API v3

1. In the left sidebar, go to **APIs & Services → Library**
2. Search for **YouTube Data API v3**
3. Click **Enable**

---

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** (unless you have a Google Workspace account)
3. Fill in required fields:
   - App name: `StreamMind`
   - User support email: your email
   - Developer contact email: your email
4. Click **Save and Continue** through the remaining steps
5. On the **Test users** step, add the email(s) that will use the app during development
6. Click **Back to Dashboard**

> **Note:** In test mode, only added test users can authorize the app. To use in production, you must submit for Google verification.

---

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Select **Web application**
4. Set the name (e.g., "StreamMind Web")
5. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:8000/api/v1/youtube/auth/callback
   ```
6. Click **Create**
7. Copy the **Client ID** and **Client Secret** — you'll need these next

---

## Step 5: Configure Environment Variables

Add to `backend/.env.development`:

```env
YOUTUBE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret-here
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/v1/youtube/auth/callback
FRONTEND_DIR=/absolute/path/to/agentic/frontend
```

> Replace `/absolute/path/to/agentic` with your actual project path, e.g.:
> `FRONTEND_DIR=/Users/yourname/projects/agentic/frontend`

---

## Step 6: Start the Application

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Classification worker
cd workers
python -m classification.worker

# Terminal 3: Embeddings worker
cd workers
python -m embeddings.worker

# Terminal 4: Clustering worker
cd workers
python -m clustering.worker

# Terminal 5: Answer generation worker
cd workers
python -m answer_generation.worker

# Terminal 6 (YouTube mode only): Polling worker
cd workers
python -m youtube_polling.worker

# Terminal 7 (YouTube mode only): Posting worker
cd workers
python -m youtube_posting.worker
```

Then open: [http://localhost:8000/app](http://localhost:8000/app)

---

## Step 7: Connect YouTube in the Dashboard

1. Register/login at `http://localhost:8000/app`
2. Click **Connect YouTube** in the YouTube panel
3. A popup appears — sign in with the test user account
4. Grant the requested permissions
5. The popup closes and the status updates to **Connected**

---

## Using YouTube Mode

1. Start a YouTube live stream from YouTube Studio
2. Copy the video ID from the stream URL:
   - URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
   - Video ID: `dQw4w9WgXcQ`
3. In the dashboard, enter the video ID when creating a session
4. Questions from your live chat auto-populate every 5 seconds
5. AI clusters similar questions and generates answers
6. Click **Approve & Post** to post answers directly to the live chat

---

## Manual Mode (No YouTube Credentials Required)

You can use the dashboard without YouTube integration:

1. Create a session without a YouTube Video ID
2. Use the **Manual Questions** panel to enter questions
3. AI classifies, clusters, and answers them
4. Use **Copy** to copy answers to clipboard

---

## Production Deployment

For production use:

1. **HTTPS is required** by Google OAuth — your redirect URI must use `https://`
2. Update the authorized redirect URI in Google Cloud Console to your production domain:
   ```
   https://yourdomain.com/api/v1/youtube/auth/callback
   ```
3. Update `YOUTUBE_REDIRECT_URI` in your production environment variables
4. Submit your OAuth consent screen for Google verification to allow any Google user (not just test users)

---

## Quota Limits

The YouTube Data API v3 has a daily quota of **10,000 units** (per project):

| Operation | Quota Cost |
|-----------|-----------|
| Get live chat ID | 1 unit |
| Poll live chat messages | 5 units |
| Post a message | 50 units |

The application tracks quota per teacher per day in Redis and automatically stops operations when the limit is approached. Quota resets at midnight UTC.

If you exceed the quota, request an increase via **APIs & Services → Quotas** in Google Cloud Console.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `redirect_uri_mismatch` | Ensure redirect URI in Google Cloud exactly matches `YOUTUBE_REDIRECT_URI` |
| `access_denied` | Add your email to test users on the OAuth consent screen |
| Popup doesn't close | Check browser popup blockers; allow popups from `localhost:8000` |
| No comments appearing | Verify stream is live and video ID is correct |
| `403 quota exceeded` | Wait until midnight UTC or request quota increase |
