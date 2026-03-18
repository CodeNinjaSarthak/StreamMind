# Shared Contracts

> Purpose: shared/ JSON schemas and TS constants — the canonical cross-platform type source.

<!-- Populate from: shared/ directory -->

## Overview

The `shared/` directory contains type definitions and constants that are used by
multiple services (backend workers, frontend, Chrome extension). This prevents
drift between services when schemas change.

## Contents

<!-- Populate from actual shared/ directory contents -->

```
shared/
├── schemas/        — JSON Schema definitions for worker payloads
└── constants/      — Shared constants (queue names, event types, etc.)
```

## Worker Payload Schemas

These schemas define the canonical shape for inter-worker messages.
They are the source of truth for both Python (`workers/common/schemas.py`) and
any TypeScript consumers.

| Schema | Used by |
|--------|---------|
| `ClassificationPayload` | classification worker (producer: polling), |
| `EmbeddingPayload` | embeddings worker |
| `ClusteringPayload` | clustering worker |
| `AnswerGenerationPayload` | answer_generation worker |
| `YouTubePostingPayload` | youtube_posting worker |

## TypeScript Constants

<!-- Document any TS constants: event type strings, queue names, error codes -->

## Usage

When adding a new field to a worker payload:
1. Update the schema in `shared/schemas/`
2. Update `workers/common/schemas.py` (Python dataclass/Pydantic model)
3. Update any TypeScript consumers in `chrome-extension/` or `frontend/`
4. Update the payload documentation in the relevant `workers/*.md` file
