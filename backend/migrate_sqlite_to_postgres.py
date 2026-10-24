
import os
import json
import sqlite3

from sqlalchemy import MetaData, create_engine, inspect, text

SOURCE_DB = os.path.join(os.path.dirname(__file__), "trustvault.db")

TABLES = [
    "users",
    "documents",
    "document_permissions",
    "audit_events",
    "incidents",
]

BOOLEAN_COLUMNS = {"is_active", "can_read", "can_edit"}


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    if not os.path.isfile(SOURCE_DB):
        raise RuntimeError(f"Source database not found: {SOURCE_DB}")

    source = sqlite3.connect(
        SOURCE_DB,
        detect_types=sqlite3.PARSE_DECLTYPES,
    )
    source.row_factory = sqlite3.Row
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        inspector = inspect(engine)

        for table in TABLES:
            if not inspector.has_table(table):
                raise RuntimeError(f"Target table missing: {table}")

        source_counts = {
            table: source.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in TABLES
        }

        metadata = MetaData()
        target_tables = {
            name: __import__("sqlalchemy").Table(
                name, metadata, autoload_with=engine
            )
            for name in TABLES
        }

        with engine.begin() as conn:
            target_counts = {
                table: conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar_one()
                for table in TABLES
            }

            if any(target_counts.values()):
                raise RuntimeError(
                    "Target tables are not empty; migration cancelled: "
                    f"{target_counts}"
                )

            for table in TABLES:
                rows = source.execute(
                    f'SELECT * FROM "{table}" ORDER BY id'
                ).fetchall()

                payload = []
                for row in rows:
                    item = dict(row)

                    for column in BOOLEAN_COLUMNS.intersection(item):
                        if item[column] is not None:
                            item[column] = bool(item[column])

                    if "metadata" in item and item["metadata"] is not None:
                        if isinstance(item["metadata"], str):
                            item["metadata"] = json.loads(item["metadata"])

                    payload.append(item)

                if payload:
                    conn.execute(target_tables[table].insert(), payload)

                actual = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar_one()

                if actual != source_counts[table]:
                    raise RuntimeError(
                        f"Count mismatch for {table}: "
                        f"expected {source_counts[table]}, got {actual}"
                    )

                print(f"{table}: verified {actual} rows")

            # Reset PostgreSQL ID sequences after importing explicit IDs.
            for table in TABLES:
                sequence = conn.execute(
                    text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
                    {"table_name": table},
                ).scalar_one_or_none()

                if sequence:
                    maximum_id = conn.execute(
                        text(f'SELECT MAX(id) FROM "{table}"')
                    ).scalar_one()

                    if maximum_id is not None:
                        conn.execute(
                            text(
                                "SELECT setval(CAST(:sequence AS regclass), "
                                ":maximum_id, true)"
                            ),
                            {
                                "sequence": sequence,
                                "maximum_id": maximum_id,
                            },
                        )

        print("Migration committed successfully.")
        print("All five table counts match the local database.")

    finally:
        source.close()
        engine.dispose()


if __name__ == "__main__":
    main()
