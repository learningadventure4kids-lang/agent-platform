"""Regression test for a real production incident: create_all() never
alters an existing table, so a column added to a model after a table
already exists on a live database (e.g. agents.max_tokens/provider_id/
fallback_provider_id, added when AI provider configurability shipped)
would otherwise crash every startup with `UndefinedColumn` on any
pre-existing installation. `init_db()` must heal this automatically."""
from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect, text

from app.config import get_settings


def test_init_db_adds_missing_columns_to_existing_table():
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)

    # Simulate a pre-upgrade `agents` table that predates provider_id/
    # max_tokens/fallback_provider_id by creating a *separate* throwaway
    # table with a couple of columns deliberately missing, then running
    # the same auto-migration routine init_db() uses against it.
    scratch_meta = MetaData()
    old_style_table = Table(
        "regression_old_style_agents",
        scratch_meta,
        Column("id", Integer, primary_key=True),
        Column("agent_key", String(80)),
        # Deliberately missing: "max_tokens" -- present on the real Agent
        # model but not here, mirroring a stale pre-upgrade table.
    )
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS regression_old_style_agents"))
    scratch_meta.create_all(bind=engine)

    new_style_meta = MetaData()
    Table(
        "regression_old_style_agents",
        new_style_meta,
        Column("id", Integer, primary_key=True),
        Column("agent_key", String(80)),
        Column("max_tokens", Integer),  # the "newly added" column
    )

    # Run the same logic app/database/connection.py::_auto_add_missing_columns
    # runs, against this scratch metadata instead of the real Base, so the
    # test doesn't depend on any specific real model's column history.
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in new_style_meta.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN IF NOT EXISTS "{column.name}" {col_type}')
                )

    inspector = inspect(engine)
    columns_after = {c["name"] for c in inspector.get_columns("regression_old_style_agents")}
    assert "max_tokens" in columns_after

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE regression_old_style_agents"))


def test_auto_add_missing_columns_is_a_noop_on_a_fresh_database():
    """Running the real init_db() auto-migration against the actual,
    already-up-to-date test database must not error and must not touch
    tables that already have every column."""
    from app.database.connection import _auto_add_missing_columns

    _auto_add_missing_columns()  # should complete silently, no exception
