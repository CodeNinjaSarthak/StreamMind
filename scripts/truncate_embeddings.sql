-- Run with: psql $DATABASE_URL -f scripts/truncate_embeddings.sql

BEGIN;

UPDATE comments SET embedding = NULL;
-- comments.embedding cleared

UPDATE clusters SET centroid_embedding = NULL;
-- clusters.centroid_embedding cleared

UPDATE rag_documents SET embedding = NULL;
-- rag_documents.embedding cleared

COMMIT;
