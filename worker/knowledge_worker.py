"""Standalone knowledge ingestion worker.

Deliberately a separate process from the FastAPI app (per the project
brief: "do NOT do upload -> extract -> chunk -> embedding -> vector
indexing inside the chat request"). Run it alongside the API:

    python worker/knowledge_worker.py

or as its own Docker Compose service (see docker-compose.yml). It's safe
to run more than one instance (WORKER_COUNT is informational for how many
processes you deploy, not a max the module enforces) -- each poll uses
`SELECT ... FOR UPDATE SKIP LOCKED` so two workers never grab the same job.

The worker itself contains no ingestion logic; it just claims a job and
hands off to app.rag.ingestion.service.process_job, which is the same code
path the test suite exercises directly.
"""
from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import text  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database.connection import SessionLocal, init_db  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.knowledge_job import STATUS_PENDING, KnowledgeJob  # noqa: E402
from app.rag.ingestion.service import process_job  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("agent_platform.worker")

_running = True


def _handle_shutdown(signum, frame):
    global _running
    logger.info("shutdown signal received, finishing current job then exiting")
    _running = False


def claim_next_job(db) -> tuple[KnowledgeJob, Document] | None:
    """Atomically claims one pending job so concurrent worker processes
    never both pick up the same one."""
    if db.bind.dialect.name == "postgresql":
        row = db.execute(
            text(
                "SELECT id FROM knowledge_jobs WHERE status = :status "
                "ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
            ),
            {"status": STATUS_PENDING},
        ).first()
    else:  # pragma: no cover -- SQLite fallback for local experimentation only
        row = db.execute(
            text("SELECT id FROM knowledge_jobs WHERE status = :status ORDER BY created_at ASC LIMIT 1"),
            {"status": STATUS_PENDING},
        ).first()

    if not row:
        return None

    job = db.query(KnowledgeJob).filter(KnowledgeJob.id == row[0]).with_for_update().first()
    if not job or job.status != STATUS_PENDING:
        return None  # another worker beat us to it

    document = db.query(Document).filter(Document.id == job.document_id).first()
    if not document:
        job.status = "FAILED"
        job.error_message = "Associated document no longer exists."
        db.commit()
        return None

    return job, document


def run_forever() -> None:
    settings = get_settings()
    init_db()
    logger.info(
        "knowledge worker started (poll_interval=%.1fs, embedding_provider=%s)",
        settings.WORKER_POLL_INTERVAL_SECONDS, settings.EMBEDDING_PROVIDER,
    )

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    while _running:
        db = SessionLocal()
        try:
            claimed = claim_next_job(db)
            if claimed is None:
                db.commit()
                time.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)
                continue

            job, document = claimed
            process_job(db, job, document)
        except Exception:
            logger.exception("worker loop error")
            db.rollback()
            time.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)
        finally:
            db.close()

    logger.info("knowledge worker stopped")


if __name__ == "__main__":
    run_forever()
