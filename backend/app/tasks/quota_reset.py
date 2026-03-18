"""Quota reset task — resets used counts for all expired quota periods."""

import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.db.models.quota import Quota
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def reset_quotas(db: Session) -> None:
    """Reset all quotas whose reset_at timestamp has passed.

    Sets used=0 and advances reset_at to the next period boundary.
    Safe to run frequently — only touches rows where reset_at <= now.
    """
    now = datetime.now(timezone.utc)

    expired = db.query(Quota).filter(Quota.reset_at <= now).all()

    if not expired:
        logger.debug("No quotas due for reset")
        return

    reset_count = 0
    for quota in expired:
        quota.used = 0
        if quota.period == "daily":
            quota.reset_at = now + timedelta(days=1)
        elif quota.period == "monthly":
            # Advance by roughly one month (30 days)
            quota.reset_at = now + timedelta(days=30)
        else:
            # Unknown period — advance by 1 day as safe fallback
            logger.warning(f"Unknown quota period '{quota.period}' for quota {quota.id}, defaulting to daily")
            quota.reset_at = now + timedelta(days=1)
        reset_count += 1

    db.commit()
    logger.info(f"Reset {reset_count} quota(s)")
