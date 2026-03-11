"""Database connection for workers."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")
_engine = create_engine(_database_url, pool_pre_ping=True)
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
