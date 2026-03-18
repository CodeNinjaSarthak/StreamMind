# YouTube Polling Worker

> Purpose: ThreadPoolExecutor per session, chat_id Redis cache, comment dedup via youtube_comment_id.

<!-- Populate from: workers/youtube_polling/worker.py -->

## Role

Polls YouTube Live Chat APIs for new comments across all active sessions in parallel.
New comments are persisted to the DB and enqueued for classification.

## Parallelism

`ThreadPoolExecutor` — one thread per active session. Sessions are polled independently. Maximum 10 concurrent threads (`max_workers=min(active_sessions, 10)`).

## chat_id Caching

The YouTube `liveChatId` for a video is resolved once (costs 1 quota unit via
`YouTubeClient.get_live_chat_id()`) and cached in Redis:

Redis key pattern: `youtube:poll:{session_id}:chat_id` (TTL: 3600s)

On cache miss: call YouTube API and cache the result.

## Comment Deduplication

`youtube_comment_id` (YouTube's own comment ID) is stored as a NOT NULL unique
field on the `Comment` model. Before inserting, the worker checks if this ID already
exists in the DB. Duplicates are silently skipped.

For manual comments (not from YouTube): `youtube_comment_id = f"manual:{uuid4()}"`

## Polling Interval

5-second full polling cycle. Each active session is polled in parallel within the cycle.

## Quota Cost

Each poll call costs **5 YouTube API quota units**.
See [data/quota-model.md](../data/quota-model.md) for enforcement.

## On New Comment

1. Persist `Comment` record to DB
2. Enqueue `ClassificationPayload` to `QUEUE_CLASSIFICATION`
3. Publish `comment_created` WebSocket event via Redis pub/sub

## Error Handling

- On 403 quota exceeded: stop polling, log error, do NOT retry immediately
  See [state/runbooks/youtube-quota-exceeded.md](../state/runbooks/youtube-quota-exceeded.md)
- On 401: OAuth token expired — trigger refresh
  See [security/youtube-oauth.md](../security/youtube-oauth.md)
