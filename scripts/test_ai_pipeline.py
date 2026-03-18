"""End-to-end test for the AI pipeline: classification → embedding → clustering → answer."""

import datetime
import os
import sys
import time
import uuid
from datetime import timezone

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

from app.db.models.answer import Answer  # noqa: E402
from app.db.models.comment import Comment  # noqa: E402
from app.db.models.streaming_session import StreamingSession  # noqa: E402
from app.db.models.teacher import Teacher  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from workers.common.queue import (  # noqa: E402
    QUEUE_CLASSIFICATION,
    QueueManager,
)
from workers.common.schemas import ClassificationPayload  # noqa: E402

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

TIMEOUT = 120  # seconds


def main():
    # Insert test data
    teacher = Teacher(email=f"test_{uuid.uuid4()}@test.com", name="Test Teacher", hashed_password="x", is_active=True)
    db.add(teacher)
    db.flush()

    session = StreamingSession(
        teacher_id=teacher.id,
        youtube_video_id=f"test_{uuid.uuid4()}",
        is_active=True,
        started_at=datetime.datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()

    # Create 5 test questions
    questions = [
        "What is photosynthesis?",
        "How does cellular respiration work?",
        "Explain the water cycle",
        "What are the phases of mitosis?",
        "How do enzymes function in cells?",
    ]

    comments = []
    manager = QueueManager()

    for i, question_text in enumerate(questions):
        comment = Comment(
            session_id=session.id,
            youtube_comment_id=f"yt_{uuid.uuid4()}",
            author_name=f"Student{i+1}",
            text=question_text,
            is_question=False,
            is_answered=False,
        )
        db.add(comment)
        db.flush()
        comments.append(comment)

        # Enqueue for classification
        manager.enqueue(
            QUEUE_CLASSIFICATION,
            ClassificationPayload(comment_id=str(comment.id), text=comment.text, session_id=str(session.id)).to_dict(),
        )

    db.commit()
    print(f"Enqueued {len(comments)} comments for classification")

    # Wait for first comment to go through all stages
    first_comment = comments[0]

    stages = [
        ("Classification", lambda c: c.is_question is not None),
        ("Embedding", lambda c: c.embedding is not None),
        ("Clustering", lambda c: c.cluster_id is not None),
        ("Answer", lambda c: db.query(Answer).filter(Answer.cluster_id == c.cluster_id).first() is not None),
    ]

    start = time.time()
    for name, check in stages:
        print(f"Waiting for {name}...")
        while time.time() - start < TIMEOUT:
            db.refresh(first_comment)
            if check(first_comment):
                print(f"  ✓ {name} complete ({time.time() - start:.1f}s)")
                break
            time.sleep(3)
        else:
            print(f"  ✗ {name} timed out after {TIMEOUT}s")

    # Cleanup
    for comment in comments:
        db.delete(comment)
    db.delete(session)
    db.delete(teacher)
    db.commit()
    print("Cleanup done")


if __name__ == "__main__":
    main()
