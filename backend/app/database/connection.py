"""SQLAlchemy engine and session management. Swapping SQLite for Postgres
later is a one-line DATABASE_URL change -- nothing else talks to sqlite3
directly, and no SQLite-only syntax is used in the models."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

logger = logging.getLogger("agent_platform.db")

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def _auto_add_missing_columns() -> None:
    """`Base.metadata.create_all()` only creates tables that don't exist
    yet -- it never alters a table that's already there. That's fine for a
    fresh database, but every time this project's models gain a new column
    on an *existing* table (as `agents.provider_id`/`max_tokens`/
    `fallback_provider_id` did when AI provider configurability was added),
    every already-running installation would otherwise crash on startup
    with `UndefinedColumn`, forever, until someone manually ran an ALTER
    TABLE.

    This adds any column present on a model but missing from the live
    table, via `ADD COLUMN IF NOT EXISTS`. It is NOT a substitute for a
    real migration tool (Alembic) for anything beyond additive nullable
    columns -- renames, drops, type changes, backfills, and NOT NULL
    constraints on existing rows all still need a real migration -- but it
    is enough to keep this project's simple additive schema changes from
    taking down an existing deployment.
    """
    if engine.dialect.name != "postgresql":
        return  # SQLite dev installs: simplest fix is deleting the file.

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # brand-new table -- create_all() already handled it
            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                logger.warning(
                    "auto-migration: adding missing column %s.%s (%s)",
                    table.name, column.name, col_type,
                )
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN IF NOT EXISTS "{column.name}" {col_type}')
                )


def init_db() -> None:
    from app.models import (  # noqa: F401
        agent,
        ai_provider,
        consultation,
        customer,
        document,
        document_chunk,
        knowledge_base,
        knowledge_job,
        lead,
        message,
        session,
        tool,
        tool_execution_log,
        user,
        user_session,
    )

    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

    Base.metadata.create_all(bind=engine)
    _auto_add_missing_columns()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
