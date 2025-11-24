#!/usr/bin/env python3
"""Initialize the SQLite database for the Career Path Navigator.

This script:
- Creates myapp.db if not present.
- Executes schema.sql idempotently to create all required tables and indices.
- Seeds minimal reference data for roles, competencies, role mappings, adjacency, and resources.
- Writes connection hints and a sqlite.env file for the db visualizer.

Environment:
- Uses local file myapp.db in the working directory (no hard-coded absolute paths).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing

DB_NAME = "myapp.db"
SCHEMA_FILE = "schema.sql"


def _run_schema(conn: sqlite3.Connection) -> None:
    """Execute schema.sql if present; otherwise no-op."""
    if not os.path.exists(SCHEMA_FILE):
        print(f"Note: {SCHEMA_FILE} not found, skipping schema execution (tables may already exist).")
        return
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
    with conn:
        conn.executescript(sql)


def _seed_minimal(conn: sqlite3.Connection) -> None:
    """Seed minimal, idempotent data to support MVP flows."""
    with conn:
        # Roles
        roles = [
            ("Chief Architect", "CA"),
            ("Chief Technology Officer", "CTO"),
            ("Chief Information Officer", "CIO"),
            ("Chief Product & Technology Officer", "CPTO"),
        ]
        for name, abbr in roles:
            conn.execute(
                "INSERT OR IGNORE INTO roles(name, abbreviation) VALUES (?,?)",
                (name, abbr),
            )

        # Competencies (subset for MVP)
        competencies = [
            ("Developer Experience & Golden Paths", "Golden paths, reference impls, CI/CD templates, telemetry"),
            ("Standards Lifecycle & Deprecations", "Adopt/Contain/Retire calls, deprecation programs"),
            ("Risk-by-Design & SLOs", "Policy-as-code, reliability, incident trends"),
            ("Portfolio & FinOps", "Cost-to-serve, platform consolidation, funding"),
        ]
        for name, definition in competencies:
            conn.execute(
                "INSERT OR IGNORE INTO competencies(name, definition) VALUES (?,?)",
                (name, definition),
            )

        # Role -> Competency matrix (simple example expectations)
        # Expected levels: P=Proficient, A=Advanced, Au=Authority
        # Map helper lookups
        role_id = {
            r["name"]: r["id"]
            for r in conn.execute("SELECT id, name FROM roles").fetchall()
        }
        comp_id = {
            c["name"]: c["id"]
            for c in conn.execute("SELECT id, name FROM competencies").fetchall()
        }

        role_comp_expected = [
            ("Chief Architect", "Developer Experience & Golden Paths", "A"),
            ("Chief Architect", "Standards Lifecycle & Deprecations", "Au"),
            ("Chief Architect", "Risk-by-Design & SLOs", "A"),
            ("Chief Architect", "Portfolio & FinOps", "P"),
            ("Chief Technology Officer", "Developer Experience & Golden Paths", "A"),
            ("Chief Technology Officer", "Standards Lifecycle & Deprecations", "A"),
            ("Chief Technology Officer", "Risk-by-Design & SLOs", "A"),
            ("Chief Technology Officer", "Portfolio & FinOps", "Au"),
        ]
        for rname, cname, level in role_comp_expected:
            r_id = role_id.get(rname)
            c_id = comp_id.get(cname)
            if r_id and c_id:
                conn.execute(
                    "INSERT OR IGNORE INTO role_competencies(role_id, competency_id, expected_level) VALUES (?,?,?)",
                    (r_id, c_id, level),
                )

        # Role adjacency (overlap % from CA to others, simple MVP numbers)
        pairs = [
            ("Chief Architect", "Chief Technology Officer", 72.0),
            ("Chief Architect", "Chief Information Officer", 58.0),
            ("Chief Architect", "Chief Product & Technology Officer", 65.0),
        ]
        for from_name, to_name, overlap in pairs:
            from_id = role_id.get(from_name)
            to_id = role_id.get(to_name)
            if from_id and to_id:
                conn.execute(
                    "INSERT OR IGNORE INTO role_adjacency(from_role_id, to_role_id, overlap_pct) VALUES (?,?,?)",
                    (from_id, to_id, overlap),
                )

        # Resources
        resources = [
            ("Golden Paths Starter", "https://example.com/golden-paths", "DX,standards"),
            ("Policy-as-Code Basics", "https://example.com/policy-as-code", "risk,SLO,governance"),
            ("FinOps for Platforms", "https://example.com/finops", "finops,portfolio,cost"),
        ]
        for title, url, tags in resources:
            # Avoid duplicates by unique(title,url)
            existing = conn.execute(
                "SELECT id FROM resources WHERE title=? AND ifnull(url,'')=ifnull(?,'')",
                (title, url),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO resources(title, url, tags) VALUES (?,?,?)",
                    (title, url, tags),
                )


def main() -> None:
    """Entry point for initializing the SQLite DB."""
    print("Starting SQLite setup...")
    db_exists = os.path.exists(DB_NAME)
    if db_exists:
        print(f"SQLite database already exists at {DB_NAME}")
    else:
        print("Creating new SQLite database...")

    # Connect with foreign keys on and row factory as dict-like
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        with conn:
            conn.execute("PRAGMA foreign_keys = ON")

        # Run schema
        _run_schema(conn)

        # Seed minimal data
        _seed_minimal(conn)

        # Compute stats
        tbl_count = conn.execute(
            "SELECT COUNT(*) AS c FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()["c"]

    # Save connection information
    current_dir = os.getcwd()
    connection_string = f"sqlite:///{current_dir}/{DB_NAME}"
    try:
        with open("db_connection.txt", "w", encoding="utf-8") as f:
            f.write("# SQLite connection methods:\n")
            f.write(f"# Python: sqlite3.connect('{DB_NAME}')\n")
            f.write(f"# Connection string: {connection_string}\n")
            f.write(f"# File path: {current_dir}/{DB_NAME}\n")
        print("Connection information saved to db_connection.txt")
    except Exception as e:
        print(f"Warning: Could not save connection info: {e}")

    # Prepare db_visualizer env
    db_path = os.path.abspath(DB_NAME)
    if not os.path.exists("db_visualizer"):
        os.makedirs("db_visualizer", exist_ok=True)
        print("Created db_visualizer directory")
    try:
        with open("db_visualizer/sqlite.env", "w", encoding="utf-8") as f:
            f.write(f'export SQLITE_DB="{db_path}"\n')
        print("Environment variables saved to db_visualizer/sqlite.env")
    except Exception as e:
        print(f"Warning: Could not save environment variables: {e}")

    print("\nSQLite setup complete!")
    print(f"Database: {DB_NAME}")
    print(f"Location: {current_dir}/{DB_NAME}")
    print(f"Tables: {tbl_count}")

    print("\nTo use with Node.js viewer, run: source db_visualizer/sqlite.env")
    print("\nTo connect:")
    print(f"1. Python: sqlite3.connect('{DB_NAME}')")
    print(f"2. Connection string: {connection_string}")
    print(f"3. Direct file access: {current_dir}/{DB_NAME}")
    print("\nScript completed successfully.")


if __name__ == "__main__":
    main()
