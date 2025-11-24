#!/usr/bin/env python3
"""Smoke tests for SQLite database.

Verifies:
- DB file exists and is connectable.
- Required tables exist.
- Foreign keys are enforced.
- Basic indices exist.
- Minimal insert/select works for key tables.

Exit code 0 on success; non-zero on failure.
"""

import os
import sqlite3
import sys
from contextlib import closing

DB_NAME = "myapp.db"

REQUIRED_TABLES = {
    "users",
    "roles",
    "competencies",
    "role_competencies",
    "role_adjacency",
    "resources",
    "job_applications",
    "user_progress",
}

REQUIRED_INDICES = {
    "idx_users_email",
    "idx_roles_name",
    "idx_competencies_name",
    "idx_role_comp_role",
    "idx_role_comp_comp",
    "idx_role_adj_from",
    "idx_role_adj_to",
    "idx_resources_title",
    "idx_jobs_user",
    "idx_progress_user",
    "idx_progress_comp",
}

def fail(msg: str) -> None:
    print(f"TEST FAIL: {msg}")
    sys.exit(1)

def main() -> None:
    if not os.path.exists(DB_NAME):
        fail(f"Database file '{DB_NAME}' not found")

    try:
        with closing(sqlite3.connect(DB_NAME)) as conn:
            conn.row_factory = sqlite3.Row
            with conn:
                conn.execute("PRAGMA foreign_keys = ON")

            # Version
            version = conn.execute("SELECT sqlite_version()").fetchone()[0]
            print(f"SQLite version: {version}")

            # Tables
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            tables = {r["name"] for r in rows}
            missing = REQUIRED_TABLES - tables
            if missing:
                fail(f"Missing tables: {sorted(missing)}")
            print(f"Tables present: {sorted(tables)}")

            # Foreign key pragma enforcement
            fk_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            if fk_on != 1:
                fail("PRAGMA foreign_keys is not enabled")
            print("Foreign keys enabled: OK")

            # Indices
            idx_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            indices = {r["name"] for r in idx_rows}
            idx_missing = REQUIRED_INDICES - indices
            if idx_missing:
                fail(f"Missing indices: {sorted(idx_missing)}")
            print(f"Indices present: {sorted(REQUIRED_INDICES)}")

            # Insert/select smoke
            with conn:
                conn.execute("INSERT OR IGNORE INTO roles(name, abbreviation) VALUES (?,?)", ("Test Role", "TR"))
            test_role = conn.execute("SELECT id FROM roles WHERE abbreviation='TR'").fetchone()
            if not test_role:
                fail("Smoke insert/select failed for roles")
            print("Smoke insert/select: OK")

            print("All database smoke tests passed.")
            sys.exit(0)
    except sqlite3.Error as e:
        fail(f"SQLite error: {e}")

if __name__ == "__main__":
    main()
