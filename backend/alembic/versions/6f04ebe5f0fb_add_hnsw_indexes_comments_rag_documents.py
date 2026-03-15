"""add hnsw indexes to comments and rag_documents embedding columns

Revision ID: 6f04ebe5f0fb
Revises: d4e5f6a7b8c9
Create Date: 2026-03-15 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6f04ebe5f0fb"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_embedding_hnsw
        ON comments
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding_hnsw
        ON rag_documents
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_rag_documents_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_comments_embedding_hnsw")
