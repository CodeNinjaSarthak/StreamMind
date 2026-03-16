"""Teacher dashboard API routes."""

import logging
from datetime import (
    datetime,
    timezone,
)
from uuid import (
    UUID,
    uuid4,
)

from app.core.security import get_current_active_user
from app.db.models.answer import Answer
from app.db.models.cluster import Cluster
from app.db.models.comment import Comment
from app.db.models.streaming_session import StreamingSession
from app.db.models.teacher import Teacher
from app.db.models.youtube_token import YouTubeToken
from app.db.session import get_db
from app.schemas.answer import (
    AnswerResponse,
    AnswerUpdate,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy import update
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


class ManualQuestionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


@router.post("/sessions/{session_id}/manual-question", status_code=status.HTTP_201_CREATED)
async def submit_manual_question(
    session_id: UUID,
    payload: ManualQuestionRequest,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create Comment(s) from manual input and enqueue for classification.

    Supports bulk input: split on newlines, up to 10 questions per request.
    """
    from workers.common.queue import (
        QUEUE_CLASSIFICATION,
        QueueManager,
    )
    from workers.common.schemas import ClassificationPayload

    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    texts = [t.strip() for t in payload.text.split("\n") if t.strip()]
    created_count = 0
    manager = QueueManager()

    for text in texts[:10]:
        comment = Comment(
            session_id=session_id,
            youtube_comment_id=f"manual:{uuid4()}",
            author_name="Teacher (Manual)",
            text=text,
        )
        db.add(comment)
        db.flush()
        manager.enqueue(
            QUEUE_CLASSIFICATION,
            ClassificationPayload(
                comment_id=str(comment.id),
                text=text,
                session_id=str(session_id),
            ).to_dict(),
        )
        created_count += 1

    db.commit()
    logger.info(f"Created {created_count} manual comment(s) for session {session_id}")
    return {"created": created_count}


@router.post("/answers/{answer_id}/approve", response_model=AnswerResponse)
async def approve_answer(
    answer_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    """Approve an answer — post to YouTube if connected, else mark posted immediately."""
    from workers.common.queue import (
        QUEUE_YOUTUBE_POSTING,
        QueueManager,
    )
    from workers.common.schemas import YouTubePostingPayload

    result = (
        db.query(Answer, Cluster, StreamingSession)
        .join(Cluster, Answer.cluster_id == Cluster.id)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Answer.id == answer_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    answer, cluster, session = result

    rows_updated = db.execute(
        update(Answer)
        .where(Answer.id == answer_id, Answer.is_posted == False)  # noqa: E712
        .values(is_posted=True, posted_at=datetime.now(timezone.utc))
    ).rowcount

    if rows_updated == 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already approved")

    db.commit()
    db.refresh(answer)

    yt_token = db.query(YouTubeToken).filter(YouTubeToken.teacher_id == current_user.id).first()

    if session.youtube_video_id and yt_token:
        manager = QueueManager()
        manager.enqueue(
            QUEUE_YOUTUBE_POSTING,
            YouTubePostingPayload(
                answer_id=str(answer.id),
                session_id=str(session.id),
            ).to_dict(),
        )
        logger.info(f"Enqueued answer {answer_id} for YouTube posting")

    return answer


@router.patch("/answers/{answer_id}", response_model=AnswerResponse)
async def edit_answer(
    answer_id: UUID,
    payload: AnswerUpdate,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    """Edit answer text."""
    result = (
        db.query(Answer, Cluster, StreamingSession)
        .join(Cluster, Answer.cluster_id == Cluster.id)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Answer.id == answer_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    answer, _, _ = result
    if payload.text is not None:
        answer.text = payload.text
    db.commit()
    db.refresh(answer)
    return answer


@router.get("/sessions/{session_id}/stats")
async def get_session_stats(
    session_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return aggregate stats for a session."""
    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    total_comments = db.query(Comment).filter(Comment.session_id == session_id).count()
    questions = db.query(Comment).filter(Comment.session_id == session_id, Comment.is_question.is_(True)).count()
    answered = db.query(Comment).filter(Comment.session_id == session_id, Comment.is_answered.is_(True)).count()
    clusters = db.query(Cluster).filter(Cluster.session_id == session_id).count()

    cluster_ids = [r.id for r in db.query(Cluster.id).filter(Cluster.session_id == session_id).all()]
    answers_generated = db.query(Answer).filter(Answer.cluster_id.in_(cluster_ids)).count() if cluster_ids else 0
    answers_posted = (
        db.query(Answer).filter(Answer.cluster_id.in_(cluster_ids), Answer.is_posted.is_(True)).count()
        if cluster_ids
        else 0
    )

    return {
        "total_comments": total_comments,
        "questions": questions,
        "answered": answered,
        "clusters": clusters,
        "answers_generated": answers_generated,
        "answers_posted": answers_posted,
    }


@router.get("/clusters/{cluster_id}/representative")
async def get_representative_question(
    cluster_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the comment whose embedding is closest to the cluster centroid."""
    from sqlalchemy import text as sa_text

    cluster = (
        db.query(Cluster)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Cluster.id == cluster_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    if cluster.centroid_embedding is None:
        raise HTTPException(status_code=404, detail="No centroid available")

    centroid_str = "[" + ",".join(str(v) for v in cluster.centroid_embedding) + "]"

    row = db.execute(
        sa_text("""
            SELECT c.id, c.text,
                   1 - (c.embedding <=> CAST(:centroid AS vector)) AS similarity
            FROM comments c
            WHERE c.cluster_id = :cluster_id
              AND c.is_question = TRUE
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:centroid AS vector)
            LIMIT 1
        """),
        {"centroid": centroid_str, "cluster_id": str(cluster_id)},
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="No representative question found")

    return {"comment_id": str(row.id), "text": row.text, "similarity": float(row.similarity)}
