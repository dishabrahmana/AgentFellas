#!/usr/bin/env python3
"""Quick database inspection tool — run from project root."""

import sqlite3
import sys
from pathlib import Path


def main() -> None:
    db_path = Path("data/worktracker.db")
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cur.fetchall()

    if not tables:
        print("No tables found.")
        return

    for table in tables:
        name = table["name"]
        cur.execute(f"SELECT COUNT(*) as cnt FROM \"{name}\"")
        count = cur.fetchone()["cnt"]
        print(f"\n{'='*50}")
        print(f"Table: {name}  ({count} rows)")

        # Show schema
        cur.execute(f"PRAGMA table_info(\"{name}\")")
        cols = cur.fetchall()
        print(f"{'Column':<25} {'Type':<15} {'Nullable':<10} {'Default'}")
        print("-" * 65)
        for col in cols:
            print(
                f"{col['name']:<25} {col['type']:<15} "
                f"{'YES' if col['notnull'] == 0 else 'NO':<10} "
                f"{col['dflt_value'] or '-'}"
            )

        # Show data sample
        if count > 0:
            cur.execute(f"SELECT * FROM \"{name}\" LIMIT 3")
            rows = cur.fetchall()
            print(f"\nSample data (up to 3 rows):")
            for row in rows:
                print(dict(row))

    conn.close()


if __name__ == "__main__":
    main()
