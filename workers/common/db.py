"""Database connection for workers."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")
# Connection budget: 15 (API) + 30 (6 workers × 5) = 45 total.
# PostgreSQL max_connections should be set to >= 60 (adds headroom).
_engine = create_engine(
    _database_url,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db_session():
    """Get database session for workers.

    Yields:
        Database session.
    """
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
