"""Database migration script."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.db.base import Base
from backend.app.db.session import engine


def run_migrations() -> None:
    """Run database migrations."""
    # TODO: Implement actual migration logic using Alembic
    print("Running migrations...")
    Base.metadata.create_all(bind=engine)
    print("Migrations completed")


if __name__ == "__main__":
    run_migrations()
