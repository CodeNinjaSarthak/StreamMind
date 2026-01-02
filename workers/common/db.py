"""Database connection for workers."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_db_session():
    """Get database session for workers.

    Yields:
        Database session.
    """
    database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

