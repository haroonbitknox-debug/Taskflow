"""Copy a read-only MariaDB snapshot into an empty, migrated PostgreSQL database."""

import argparse
import os
from typing import Any

from sqlalchemy import MetaData, create_engine, func, select, text
from sqlalchemy.engine import Engine

from app import models  # noqa: F401
from app.core.config import settings
from app.db.base import Base

NEW_TABLES = {"password_reset_tokens", "rate_limit_buckets"}
INTERNAL_TABLES = {"alembic_version"}
BATCH_SIZE = 500


def _table_count(engine: Engine, table: Any) -> int:
    with engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table)) or 0


def _count_rows(engine: Engine, tables: list[Any]) -> dict[str, int]:
    return {
        table.name: _table_count(engine, table)
        for table in tables
        if table.name not in INTERNAL_TABLES
    }


def _check_empty_target(target: Engine) -> None:
    for table in Base.metadata.sorted_tables:
        count = _table_count(target, table)
        if count:
            raise RuntimeError(
                f"Target table {table.name!r} is not empty ({count} rows); "
                "refusing to merge or overwrite data."
            )


def _copy_rows(
    source: Engine,
    target: Engine,
    source_metadata: MetaData,
    source_counts: dict[str, int],
) -> None:
    with source.connect() as source_connection, target.begin() as target_connection:
        for target_table in Base.metadata.sorted_tables:
            if target_table.name in NEW_TABLES:
                continue
            source_table = source_metadata.tables[target_table.name]
            target_names = set(target_table.c.keys())
            source_names = set(source_table.c.keys())
            missing = target_names - source_names
            required_missing = [
                target_table.c[name].name
                for name in missing
                if not target_table.c[name].nullable
                and target_table.c[name].default is None
                and target_table.c[name].server_default is None
                and not target_table.c[name].primary_key
                and not target_table.c[name].autoincrement
            ]
            if required_missing:
                raise RuntimeError(
                    f"Source table {target_table.name!r} is missing required "
                    f"columns: {', '.join(required_missing)}."
                )
            common_columns = [name for name in target_table.c.keys() if name in source_names]
            result = source_connection.execute(
                select(*(source_table.c[name] for name in common_columns))
            )
            while batch := result.mappings().fetchmany(BATCH_SIZE):
                records = [
                    {name: row[name] for name in common_columns}
                    for row in batch
                ]
                target_connection.execute(target_table.insert(), records)

        for target_table in Base.metadata.sorted_tables:
            if target_table.name in NEW_TABLES:
                continue
            expected = source_counts[target_table.name]
            actual = target_connection.scalar(
                select(func.count()).select_from(target_table)
            )
            if actual != expected:
                raise RuntimeError(
                    f"Row-count verification failed for {target_table.name!r}: "
                    f"source={expected}, target={actual}."
                )

        for target_table in Base.metadata.sorted_tables:
            id_column = target_table.c.get("id")
            if id_column is None or target_table.name in NEW_TABLES:
                continue
            sequence_name = target_connection.scalar(
                text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
                {"table_name": target_table.name},
            )
            maximum_id = target_connection.scalar(
                select(func.max(id_column))
            )
            if sequence_name and maximum_id is not None:
                target_connection.execute(
                    text(
                        "SELECT setval(CAST(:sequence_name AS regclass), "
                        ":maximum_id, true)"
                    ),
                    {"sequence_name": sequence_name, "maximum_id": maximum_id},
                )


def migrate(dry_run: bool = False) -> None:
    source_url = os.getenv("SOURCE_DATABASE_URL")
    if not source_url:
        raise ValueError("Set SOURCE_DATABASE_URL to the source MariaDB URL.")

    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None, "connect_timeout": 10},
    )
    try:
        if source_engine.dialect.name != "mysql":
            raise ValueError("SOURCE_DATABASE_URL must use mysql+pymysql.")
        if target_engine.dialect.name != "postgresql":
            raise ValueError("DATABASE_URL must point to PostgreSQL.")
        if source_engine.url == target_engine.url:
            raise ValueError("Source and target database URLs must be different.")

        source_metadata = MetaData()
        source_metadata.reflect(bind=source_engine)
        source_tables = set(source_metadata.tables) - INTERNAL_TABLES
        required_tables = set(Base.metadata.tables) - NEW_TABLES
        missing_tables = required_tables - source_tables
        if missing_tables:
            raise RuntimeError(
                "Source schema is missing required TaskFlow tables: "
                + ", ".join(sorted(missing_tables))
            )

        _check_empty_target(target_engine)
        taskflow_source_tables = [
            source_metadata.tables[name]
            for name in Base.metadata.tables
            if name not in NEW_TABLES
        ]
        source_counts = _count_rows(source_engine, taskflow_source_tables)
        for name, count in sorted(source_counts.items()):
            print(f"{name}: {count} source rows")
        if dry_run:
            print("Dry run complete. No data was copied.")
            return

        _copy_rows(source_engine, target_engine, source_metadata, source_counts)
        target_counts = _count_rows(
            target_engine,
            [Base.metadata.tables[name] for name in source_counts],
        )
        mismatches = {
            name: (source_count, target_counts.get(name, 0))
            for name, source_count in source_counts.items()
            if source_count != target_counts.get(name, 0)
        }
        if mismatches:
            details = ", ".join(
                f"{table}: source={source_count}, target={target_count}"
                for table, (source_count, target_count) in mismatches.items()
            )
            raise RuntimeError(f"Row-count verification failed: {details}")
        print("Migration complete. All source table row counts match PostgreSQL.")
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show source row counts and verify that the target is empty.",
    )
    arguments = parser.parse_args()
    migrate(dry_run=arguments.dry_run)
