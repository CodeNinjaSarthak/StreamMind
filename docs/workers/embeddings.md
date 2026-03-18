# Embeddings Worker

> Purpose: EmbeddingPayload → 768-dim vector stored in pgvector → enqueue to clustering queue.

<!-- Populate from: workers/embeddings/worker.py, workers/common/schemas.py -->

## Input Payload

`EmbeddingPayload` (from `workers/common/schemas.py`):

```json
{
  "comment_id": "uuid",
  "session_id": "uuid",
  "text": "string"
}
```

## Processing

1. Call `GeminiClient.generate_embedding(text)`
2. Store 768-dim vector in `Comment.embedding` (pgvector column)
3. Enqueue `ClusteringPayload` to `QUEUE_CLUSTERING`

## Embedding Model

- Provider: Google Gemini (`gemini-embedding-001`)
- Dimensions: 768
- Storage: `pgvector` `Vector(768)` column on `Comment` model
- Indexing: HNSW index (`vector_cosine_ops`, m=16, ef_construction=64)

See [architecture/decisions/ADR-001-pgvector.md](../architecture/decisions/ADR-001-pgvector.md)
for the rationale for pgvector.

## Output

Enqueues to `QUEUE_CLUSTERING`. See [workers/clustering.md](clustering.md).

## DB Updates

| Field | Value |
|-------|-------|
| `Comment.embedding` | `Vector(768)` |

For field definitions see [data/schema.md](../data/schema.md).
