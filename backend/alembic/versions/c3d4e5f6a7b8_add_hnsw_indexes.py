"""add_hnsw_indexes

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-09 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_embedding_hnsw
        ON comments
        USING hnsw (embedding vector_l2_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding_hnsw
        ON rag_documents
        USING hnsw (embedding vector_l2_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_rag_documents_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_comments_embedding_hnsw")
