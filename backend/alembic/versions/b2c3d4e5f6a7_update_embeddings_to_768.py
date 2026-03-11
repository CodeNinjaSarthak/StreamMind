"""update_embeddings_to_768

Revision ID: b2c3d4e5f6a7
Revises: 8e88e85ffe40
Create Date: 2026-02-27 21:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "8e88e85ffe40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Vector columns cannot be cast 1536→768, use DROP + ADD
    op.drop_column("comments", "embedding")
    op.add_column("comments", sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=768), nullable=True))

    op.drop_column("clusters", "centroid_embedding")
    op.add_column("clusters", sa.Column("centroid_embedding", pgvector.sqlalchemy.Vector(dim=768), nullable=True))

    op.drop_column("rag_documents", "embedding")
    op.add_column("rag_documents", sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=768), nullable=True))

    # Add teacher_id ownership to rag_documents
    op.add_column("rag_documents", sa.Column("teacher_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_rag_documents_teacher_id", "rag_documents", "teachers", ["teacher_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("fk_rag_documents_teacher_id", "rag_documents", type_="foreignkey")
    op.drop_column("rag_documents", "teacher_id")

    op.drop_column("rag_documents", "embedding")
    op.add_column("rag_documents", sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=1536), nullable=True))

    op.drop_column("clusters", "centroid_embedding")
    op.add_column("clusters", sa.Column("centroid_embedding", pgvector.sqlalchemy.Vector(dim=1536), nullable=True))

    op.drop_column("comments", "embedding")
    op.add_column("comments", sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=1536), nullable=True))
