"""
Migration helper to add semantic columns to the existing `edges` table and
populate them from legacy `flag` / `verifier_status` values where possible.

This script is safe to re-run: it will only add missing columns.
"""
from sqlalchemy import create_engine, text
from GraphEngine.db.connection import DATABASE_URL


def column_exists(conn, table: str, column: str) -> bool:
    res = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    return any(row[1] == column for row in res)


def run_migration():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Add new columns if missing
        needed = [
            ("relation_type", "TEXT"),
            ("confidence_state", "TEXT"),
            ("verifier_state", "TEXT"),
        ]

        for col, coltype in needed:
            if not column_exists(conn, "edges", col):
                print(f"Adding column {col} to edges table...")
                conn.execute(text(f"ALTER TABLE edges ADD COLUMN {col} {coltype}"))

        # Populate new columns from legacy 'flag' and 'verifier_status'
        print("Populating semantic columns from legacy data where possible...")
        # relation_type mapping
        conn.execute(text(
            "UPDATE edges SET relation_type = 'CONTRADICT' WHERE flag LIKE '%CONTRADICT%';"
        ))
        conn.execute(text(
            "UPDATE edges SET relation_type = 'SUPPORT' WHERE flag LIKE '%SUPPORT%';"
        ))
        conn.execute(text(
            "UPDATE edges SET relation_type = 'MIXED' WHERE relation_type IS NULL AND (flag IS NOT NULL OR flag='');"
        ))

        # confidence_state mapping
        conn.execute(text(
            "UPDATE edges SET confidence_state = 'LOW_CONFIDENCE' WHERE flag LIKE 'LOW_CONFIDENCE%';"
        ))
        conn.execute(text(
            "UPDATE edges SET confidence_state = 'HIGH_CONFIDENCE' WHERE confidence_state IS NULL AND (confidence >= 0.5);"
        ))

        # verifier_state from verifier_status
        conn.execute(text(
            "UPDATE edges SET verifier_state = UPPER(verifier_status) WHERE verifier_state IS NULL AND verifier_status IS NOT NULL;"
        ))

        print("Migration complete.")


if __name__ == '__main__':
    run_migration()
