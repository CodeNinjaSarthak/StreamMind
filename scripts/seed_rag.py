"""Script to seed RAG documents."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.db.session import SessionLocal


def seed_rag_documents() -> None:
    """Seed RAG documents into the database."""
    db = SessionLocal()
    try:
        # TODO: Implement actual RAG document seeding
        print("Seeding RAG documents...")
        print("RAG seeding completed")
    finally:
        db.close()


if __name__ == "__main__":
    seed_rag_documents()
