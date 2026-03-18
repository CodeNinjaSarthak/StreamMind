# Data Flow

> Purpose: Numbered end-to-end pipeline — comment ingest → classify → embed → cluster → answer → approve → post.

<!-- Populate from: docs/_archive/architecture.md (data-flow steps section) -->

## The 9-Step Comment-to-Answer Pipeline

```
[YouTube Live Chat]
        │
        ▼ (1) Poll
[youtube_polling worker]
        │ youtube_comment_id dedup
        ▼ (2) Persist + Enqueue
[Comment record (DB)] ──► QUEUE_CLASSIFICATION
        │
        ▼ (3) Classify
[classification worker]
        │ is_question=True/False, confidence_score
        ▼ (4) Enqueue if question
QUEUE_EMBEDDING
        │
        ▼ (5) Embed
[embeddings worker]
        │ 768-dim vector → pgvector
        ▼ (6) Enqueue
QUEUE_CLUSTERING
        │
        ▼ (7) Cluster
[clustering worker]
        │ cosine similarity ≥ 0.65 → assign to cluster
        ▼ (8) Enqueue
QUEUE_ANSWER_GENERATION
        │
        ▼ (9a) Generate Answer
[answer_generation worker]
        │ RAG retrieval + LLM call → Answer record (is_posted=False)
        ▼
[Teacher Dashboard] ──► approve/edit
        │
        ▼ (9b) Post
[youtube_posting worker]
        │ YouTube API → is_posted=True, answer_posted WS event
        ▼
[YouTube Live Chat]
```

## Step Details

### Step 1 — Poll
<!-- ThreadPoolExecutor, chat_id Redis cache, polling interval. See workers/youtube-polling.md -->

### Step 2 — Persist + Enqueue
<!-- Comment model fields set, youtube_comment_id NOT NULL (manual: "manual:{uuid4()}"). See data/schema.md -->

### Step 3 — Classify
<!-- Gemini call, updates Comment.is_question + confidence_score. See workers/classification.md -->

### Step 4 — Filter
<!-- Only is_question=True comments proceed to embedding. Threshold configurable. -->

### Step 5 — Embed
<!-- Gemini embedding API, 768-dim, stored as pgvector. See workers/embeddings.md -->

### Step 6–7 — Cluster
<!-- Cosine similarity at threshold 0.65, centroid update, Cluster CRUD. See workers/clustering.md -->

### Step 8–9a — Generate Answer
<!-- RAG retrieval from document store, LLM call with context. See workers/answer-generation.md -->

### Step 9b — Post
<!-- Teacher approves via dashboard; youtube_posting worker posts to YouTube API. See workers/youtube-posting.md -->

## Manual Comment Path

<!-- Manual comments submitted via dashboard bypass polling. youtube_comment_id = "manual:{uuid4()}" -->

## WebSocket Events at Each Step

<!-- Cross-reference api/websocket-events.md for the exact events emitted at each pipeline stage -->
See [api/websocket-events.md](../api/websocket-events.md) for the full event payload reference.
