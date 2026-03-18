# Backend Services

> Purpose: GeminiClient, RAG document service, YouTubeClient, quota.py, rate limiter, and moderation.

<!-- Populate from: backend/app/services/ -->

## GeminiClient

`backend/app/services/gemini/client.py` (verify path)

| Method | Purpose | Used by |
|--------|---------|---------|
| `classify_question()` | Returns `is_question`, `confidence_score` | classification worker |
| `generate_embedding()` | Returns 768-dim vector | embeddings worker |
| `generate_answer()` | Returns answer text given context | answer_generation worker |
| `summarize_cluster()` | Returns cluster title summary | clustering worker (at count=3) |

## RAG Document Service

`backend/app/services/rag/` (verify path)

- Upload documents → chunk → embed → store in pgvector
- Retrieve relevant chunks by cosine similarity for answer generation
- See [api/rest.md](../api/rest.md) for document upload endpoints

## YouTubeClient

`backend/app/services/youtube/client.py`

Wraps `google-api-python-client`. Key methods:
- `get_live_chat_id(video_id)` — resolves chat_id from video; costs 1 quota unit
- `poll_live_chat(chat_id, page_token)` — fetches new messages; costs 5 quota units
- `post_message(chat_id, message)` — posts to live chat; costs 50 quota units

See [data/quota-model.md](../data/quota-model.md) for quota enforcement.

## YouTube Quota

`backend/app/services/youtube/quota.py`

Redis-backed quota tracker. Costs per operation:
- poll: 5 units
- post: 50 units
- get_chat_id: 1 unit

See [data/quota-model.md](../data/quota-model.md) for full details.

## YouTube OAuth

`backend/app/services/youtube/oauth.py`

Flow-based OAuth. Returns `(url, state)` tuple.
Full OAuth flow documented in [security/youtube-oauth.md](../security/youtube-oauth.md).

## Rate Limiter

<!-- Redis-backed rate limiter; per-IP or per-user limits; config keys -->
See [api/error-codes.md](../api/error-codes.md) for rate limit response headers.

## Moderation

<!-- Content moderation service if applicable -->
