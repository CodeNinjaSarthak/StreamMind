"""Scheduler worker — runs periodic maintenance tasks via APScheduler."""

import logging
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

from workers.common.prometheus_setup import setup_multiproc_dir  # noqa: E402

setup_multiproc_dir()

from app.tasks.quota_reset import reset_quotas  # noqa: E402
from app.tasks.token_cleanup import cleanup_expired_tokens  # noqa: E402
from apscheduler.schedulers.blocking import BlockingScheduler  # noqa: E402
from apscheduler.triggers.cron import CronTrigger  # noqa: E402
from apscheduler.triggers.interval import IntervalTrigger  # noqa: E402

from workers.common.db import get_db_session  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_quota_reset() -> None:
    """Wrapper that opens a DB session and runs the quota reset task."""
    logger.info("Running scheduled quota reset...")
    try:
        for db in get_db_session():
            try:
                reset_quotas(db)
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Quota reset failed: {e}", exc_info=True)


def run_token_cleanup() -> None:
    """Wrapper that opens a DB session and runs the token cleanup task."""
    logger.info("Running scheduled token cleanup...")
    try:
        for db in get_db_session():
            try:
                cleanup_expired_tokens(db)
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Token cleanup failed: {e}", exc_info=True)


def main() -> None:
    """Start the APScheduler with all maintenance jobs."""
    scheduler = BlockingScheduler(timezone="UTC")

    # Quota reset — daily at midnight UTC
    scheduler.add_job(
        run_quota_reset,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="quota_reset",
        name="Daily quota reset",
        max_instances=1,
        misfire_grace_time=300,  # 5 min — run even if we were down at midnight
    )

    # Token cleanup — every hour
    scheduler.add_job(
        run_token_cleanup,
        trigger=IntervalTrigger(hours=1),
        id="token_cleanup",
        name="Hourly token cleanup",
        max_instances=1,
        misfire_grace_time=120,
    )

    logger.info("Scheduler starting — jobs registered:")
    for job in scheduler.get_jobs():
        logger.info(f"  [{job.id}] {job.name}")

    try:
        scheduler.start()
        for job in scheduler.get_jobs():
            logger.info(f"  [{job.id}] scheduled — next run: {job.next_run_time}")
    except KeyboardInterrupt:
        logger.info("Scheduler shutting down gracefully")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
