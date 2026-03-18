"""Prometheus multiprocess mode bootstrap.

Must be called BEFORE any import of prometheus_client.
"""

import glob
import os

MULTIPROC_DIR = "/tmp/prometheus_multiproc"


def setup_multiproc_dir(clear=False):
    """Set PROMETHEUS_MULTIPROC_DIR and create the directory.

    Args:
        clear: If True, remove stale .db files (only FastAPI startup should do this).
    """
    os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", MULTIPROC_DIR)
    os.makedirs(MULTIPROC_DIR, exist_ok=True)
    if clear:
        for f in glob.glob(os.path.join(MULTIPROC_DIR, "*.db")):
            os.unlink(f)
