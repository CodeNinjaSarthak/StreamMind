"""recreate clusters centroid hnsw index with tuning params

Revision ID: 6fe440076f64
Revises: 6f04ebe5f0fb
Create Date: 2026-03-15 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6fe440076f64"
down_revision = "6f04ebe5f0fb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS clusters_centroid_hnsw_idx")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_clusters_centroid_embedding_hnsw
        ON clusters
        USING hnsw (centroid_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_clusters_centroid_embedding_hnsw")
    op.execute("""
        CREATE INDEX IF NOT EXISTS clusters_centroid_hnsw_idx
        ON clusters
        USING hnsw (centroid_embedding vector_cosine_ops)
    """)
