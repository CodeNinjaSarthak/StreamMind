"""Verify data integrity of mock YouTube ingestion pipeline."""

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "backend"))

os.environ.setdefault("ENVIRONMENT", "development")

from app.db.models.answer import Answer  # noqa: E402
from app.db.models.cluster import Cluster  # noqa: E402
from app.db.models.comment import Comment  # noqa: E402
from sqlalchemy import (  # noqa: E402
    case,
    func,
)

from workers.common.db import get_db_session  # noqa: E402


def run():
    for db in get_db_session():
        try:
            # ---------------------------------------------------------------
            # 1. Total mock comments
            # ---------------------------------------------------------------
            total_mock = db.query(func.count(Comment.id)).filter(Comment.youtube_comment_id.like("mock:%")).scalar()
            print("=" * 60)
            print(f"1) TOTAL MOCK COMMENTS: {total_mock}")
            print("=" * 60)

            if total_mock == 0:
                print("   No mock comments found. Nothing to verify.")
                return

            # ---------------------------------------------------------------
            # 2. Comments grouped by cluster — first 3 texts per cluster
            # ---------------------------------------------------------------
            print("\n2) COMMENTS BY CLUSTER (first 3 per cluster)")
            print("-" * 60)

            # Unclustered
            unclustered = (
                db.query(func.count(Comment.id))
                .filter(
                    Comment.youtube_comment_id.like("mock:%"),
                    Comment.cluster_id.is_(None),
                )
                .scalar()
            )
            print(f"\n  [UNCLUSTERED] — {unclustered} comments")
            if unclustered:
                samples = (
                    db.query(Comment.text)
                    .filter(
                        Comment.youtube_comment_id.like("mock:%"),
                        Comment.cluster_id.is_(None),
                    )
                    .limit(3)
                    .all()
                )
                for i, (text,) in enumerate(samples, 1):
                    print(f'    {i}. "{text}"')

            # Clustered
            cluster_rows = (
                db.query(
                    Cluster.id,
                    Cluster.title,
                    func.count(Comment.id).label("cnt"),
                )
                .join(Comment, Comment.cluster_id == Cluster.id)
                .filter(Comment.youtube_comment_id.like("mock:%"))
                .group_by(Cluster.id, Cluster.title)
                .order_by(func.count(Comment.id).desc())
                .all()
            )

            for cid, title, cnt in cluster_rows:
                print(f'\n  Cluster: "{title}"  ({cnt} mock comments)')
                samples = (
                    db.query(Comment.text)
                    .filter(Comment.cluster_id == cid, Comment.youtube_comment_id.like("mock:%"))
                    .limit(3)
                    .all()
                )
                for i, (text,) in enumerate(samples, 1):
                    print(f'    {i}. "{text}"')

            # ---------------------------------------------------------------
            # 3. Answers generated for mock clusters
            # ---------------------------------------------------------------
            print(f"\n{'=' * 60}")
            print("3) ANSWERS FOR MOCK CLUSTERS")
            print("-" * 60)

            mock_cluster_ids = [cid for cid, _, _ in cluster_rows]
            if mock_cluster_ids:
                answers = (
                    db.query(Answer.id, Cluster.title, Answer.text, Answer.is_posted)
                    .join(Cluster, Answer.cluster_id == Cluster.id)
                    .filter(Answer.cluster_id.in_(mock_cluster_ids))
                    .order_by(Answer.created_at.desc())
                    .all()
                )
                print(f"   Total answers: {len(answers)}")
                for aid, ctitle, atext, posted in answers:
                    status = "POSTED" if posted else "pending"
                    preview = atext[:120].replace("\n", " ") + ("..." if len(atext) > 120 else "")
                    print(f'\n   [{status}] Cluster: "{ctitle}"')
                    print(f"   Answer: {preview}")
            else:
                print("   No clusters with mock comments — no answers to check.")

            # ---------------------------------------------------------------
            # 4. Classification accuracy: is_question breakdown
            # ---------------------------------------------------------------
            print(f"\n{'=' * 60}")
            print("4) CLASSIFICATION BREAKDOWN (mock comments)")
            print("-" * 60)

            stats = (
                db.query(
                    func.count(Comment.id).label("total"),
                    func.sum(case((Comment.is_question.is_(True), 1), else_=0)).label("questions"),
                    func.sum(case((Comment.is_question.is_(False), 1), else_=0)).label("non_questions"),
                )
                .filter(Comment.youtube_comment_id.like("mock:%"))
                .one()
            )

            total, questions, non_questions = (
                int(stats.total),
                int(stats.questions or 0),
                int(stats.non_questions or 0),
            )
            q_pct = (questions / total * 100) if total else 0
            nq_pct = (non_questions / total * 100) if total else 0

            print(f"   Total:         {total}")
            print(f"   is_question:   {questions}  ({q_pct:.1f}%)")
            print(f"   non-question:  {non_questions}  ({nq_pct:.1f}%)")

            # Expected: clusters A, B, D are questions (15/20 = 75%), C is not (5/20 = 25%)
            print("\n   Expected ratio: ~75% questions / ~25% non-questions")
            print(f"   Actual ratio:   {q_pct:.1f}% questions / {nq_pct:.1f}% non-questions")

            if 55 <= q_pct <= 90:
                print("   -> Classification looks REASONABLE")
            elif total > 0:
                print("   -> Classification ratio is OUTSIDE expected range — review classifier")

            print(f"\n{'=' * 60}")
            print("VERIFICATION COMPLETE")
            print("=" * 60)

        finally:
            db.close()


if __name__ == "__main__":
    run()
