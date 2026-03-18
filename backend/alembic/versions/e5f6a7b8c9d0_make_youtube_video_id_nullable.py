"""make youtube_video_id nullable

Revision ID: e5f6a7b8c9d0
Revises: 6fe440076f64, d4e5f6a7b8c9
Create Date: 2026-03-18 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = ("6fe440076f64", "d4e5f6a7b8c9")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("streaming_sessions", "youtube_video_id", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE streaming_sessions SET youtube_video_id = '' WHERE youtube_video_id IS NULL")
    op.alter_column("streaming_sessions", "youtube_video_id", nullable=False)
