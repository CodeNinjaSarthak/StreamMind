# Clustering Worker

> Purpose: ClusteringPayload → cosine similarity at threshold 0.65 → Cluster CRUD → enqueue to answer_generation.

<!-- Populate from: workers/clustering/worker.py, workers/common/schemas.py -->

## Input Payload

`ClusteringPayload` (from `workers/common/schemas.py`):

```json
{
  "comment_id": "uuid",
  "session_id": "uuid"
}
```

## Processing

1. Load `Comment.embedding` from DB
2. Query existing `Cluster` centroids for this session (pgvector cosine similarity)
3. If similarity ≥ 0.65: assign comment to that cluster, update centroid
4. If no cluster found: create a new `Cluster` with this comment as seed
5. Enqueue `AnswerGenerationPayload` to `QUEUE_ANSWER_GENERATION`

## Similarity Threshold

Default: `0.65` (cosine similarity, configurable via `clustering_similarity_threshold` in settings). Higher = stricter grouping.

## Centroid Update

When a comment joins an existing cluster, the centroid is recalculated:

```python
new_centroid = (old_centroid * comment_count + new_embedding) / (comment_count + 1)
normalized_centroid = new_centroid / ||new_centroid||  # L2 normalize
```

The `comment_count` is denormalized on the Cluster model for this formula.

## DB Operations

| Operation | Condition |
|-----------|-----------|
| `UPDATE Cluster.centroid` | Comment assigned to existing cluster |
| `INSERT Cluster` | No matching cluster found |
| `INSERT ClusterComment` (or FK update) | Always — links comment to cluster |

For field definitions see [data/schema.md](../data/schema.md).

## Output

Enqueues to `QUEUE_ANSWER_GENERATION`. See [workers/answer-generation.md](answer-generation.md).

## Answer Generation Triggers

Answer generation is NOT triggered for every clustered comment. The clustering worker enqueues to `QUEUE_ANSWER_GENERATION` only when:
- A **new cluster** is created, OR
- A cluster reaches comment count milestones: **3, 10, 25**

At count 3, the cluster title is also summarized via Gemini.
