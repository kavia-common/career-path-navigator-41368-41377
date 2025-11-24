#!/usr/bin/env python3
"""Optional JSON ingestion for seeding SQLite from backend/data JSON files.

This script is safe to run multiple times. It will:
- Load JSON datasets from the backend path (default):
  ../career-path-navigator-41368-41378/career_navigator_backend/data
  or override with BACKEND_DATA_DIR env var.
- Upsert into tables with idempotent logic using natural keys:
  roles, competencies, role_competencies, role_adjacency, resources.
- Print counts per table and write a summary file (ingestion_summary.txt).

Notes:
- Assumes schema.sql applied (run init_db.py first).
- Skips unknown files gracefully and validates inputs.

PySecure-4-Minimal-Standard:
- Input validation, exception handling, safe resource cleanup.
- No sensitive logs; follows PEP-8 and adds docstrings.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from typing import Any, Dict, Iterable, List, Optional, Tuple

DB_NAME = "myapp.db"
# Default backend data directory (sibling workspace path)
DEFAULT_DATA_DIR = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "career-path-navigator-41368-41378",
        "career_navigator_backend",
        "data",
    )
)

# PUBLIC_INTERFACE
def normalize_name(value: Optional[str]) -> Optional[str]:
    """Normalize a name-like string (trim; collapse whitespace)."""
    if value is None:
        return None
    v = " ".join(str(value).split()).strip()
    return v if v else None

def _safe_load_json(path: str) -> Any:
    """Safely load a JSON file, returning None on error or file-missing."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load {path}: {e}")
        return None

def _ensure_conn() -> sqlite3.Connection:
    """Create a sqlite3 connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _get_role_id(conn: sqlite3.Connection, name: str) -> Optional[int]:
    row = conn.execute("SELECT id FROM roles WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row else None

def _get_competency_id(conn: sqlite3.Connection, name: str) -> Optional[int]:
    row = conn.execute("SELECT id FROM competencies WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row else None

def ingest_roles(roles_json: Iterable[Dict[str, Any]], conn: sqlite3.Connection) -> int:
    """Upsert roles using unique natural key 'name'. Returns rows inserted."""
    if not roles_json:
        return 0
    inserted = 0
    with conn:
        for r in roles_json:
            name = normalize_name(r.get("name"))
            abbr = normalize_name(r.get("abbreviation"))
            if not name:
                continue
            before_changes = conn.total_changes
            conn.execute(
                "INSERT OR IGNORE INTO roles(name, abbreviation) VALUES (?, ?)",
                (name, abbr),
            )
            # If abbreviation provided later, update if NULL and no conflict
            if abbr:
                conn.execute(
                    "UPDATE roles SET abbreviation = COALESCE(abbreviation, ?) WHERE name = ?",
                    (abbr, name),
                )
            if conn.total_changes > before_changes:
                inserted += 1
    return inserted

def ingest_competencies(defs_json: Iterable[Dict[str, Any]], conn: sqlite3.Connection) -> int:
    """Upsert competencies using unique natural key 'name'. Returns rows inserted."""
    if not defs_json:
        return 0
    inserted = 0
    with conn:
        for c in defs_json:
            name = normalize_name(c.get("competency")) or normalize_name(c.get("name"))
            definition = c.get("definition") or c.get("description")
            if not name:
                continue
            before_changes = conn.total_changes
            conn.execute(
                "INSERT OR IGNORE INTO competencies(name, definition) VALUES (?, ?)",
                (name, definition),
            )
            # Update definition if previously null and now provided
            if definition:
                conn.execute(
                    "UPDATE competencies SET definition = COALESCE(definition, ?) WHERE name = ?",
                    (definition, name),
                )
            if conn.total_changes > before_changes:
                inserted += 1
    return inserted

def ingest_resources(resources_json: Iterable[Dict[str, Any]], conn: sqlite3.Connection) -> int:
    """Insert resources if not already present by (title,url). Returns rows inserted."""
    if not resources_json:
        return 0
    inserted = 0
    with conn:
        for r in resources_json:
            title = normalize_name(r.get("title"))
            url = normalize_name(r.get("url"))
            tags_val = r.get("tags")
            tags = ",".join(tags_val) if isinstance(tags_val, list) else (tags_val if isinstance(tags_val, str) else None)
            if not title:
                continue
            exists = conn.execute(
                "SELECT 1 FROM resources WHERE title=? AND ifnull(url,'')=ifnull(?, '')",
                (title, url),
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO resources(title, url, tags) VALUES (?, ?, ?)",
                    (title, url, tags),
                )
                inserted += 1
    return inserted

def ingest_role_competencies(matrix_json: Any, conn: sqlite3.Connection) -> Tuple[int, int]:
    """Upsert role_competencies from a matrix-like JSON.

    Supports two shapes:
    - List of dicts with {role, competency, expected_level}
    - Object with { roles: [...], competencies: [...], matrix: [[level,..], ...] }

    Returns: (inserted, updated) counts.
    """
    if not matrix_json:
        return (0, 0)
    ins = 0
    upd = 0
    with conn:
        # Case 1: explicit triplets
        if isinstance(matrix_json, list):
            for item in matrix_json:
                role_name = normalize_name(item.get("role"))
                comp_name = normalize_name(item.get("competency"))
                level = normalize_name(item.get("expected_level")) or normalize_name(item.get("level"))
                if not role_name or not comp_name or not level:
                    continue
                r_id = _get_role_id(conn, role_name)
                c_id = _get_competency_id(conn, comp_name)
                if not r_id or not c_id:
                    continue
                before_changes = conn.total_changes
                conn.execute(
                    "INSERT OR IGNORE INTO role_competencies(role_id, competency_id, expected_level) VALUES (?,?,?)",
                    (r_id, c_id, level),
                )
                if conn.total_changes > before_changes:
                    ins += 1
                else:
                    # Update level if different
                    cur = conn.execute(
                        "SELECT expected_level FROM role_competencies WHERE role_id=? AND competency_id=?",
                        (r_id, c_id),
                    ).fetchone()
                    if cur and cur["expected_level"] != level:
                        conn.execute(
                            "UPDATE role_competencies SET expected_level=? WHERE role_id=? AND competency_id=?",
                            (level, r_id, c_id),
                        )
                        upd += 1

        # Case 2: matrix form
        elif isinstance(matrix_json, dict):
            roles = [normalize_name(x) for x in (matrix_json.get("roles") or [])]
            comps = [normalize_name(x) for x in (matrix_json.get("competencies") or [])]
            matrix = matrix_json.get("matrix") or []
            for r_index, row in enumerate(matrix):
                role_name = roles[r_index] if r_index < len(roles) else None
                if not role_name:
                    continue
                r_id = _get_role_id(conn, role_name)
                if not r_id:
                    continue
                for c_index, level in enumerate(row):
                    comp_name = comps[c_index] if c_index < len(comps) else None
                    level_n = normalize_name(level)
                    if not comp_name or not level_n:
                        continue
                    c_id = _get_competency_id(conn, comp_name)
                    if not c_id:
                        continue
                    before_changes = conn.total_changes
                    conn.execute(
                        "INSERT OR IGNORE INTO role_competencies(role_id, competency_id, expected_level) VALUES (?,?,?)",
                        (r_id, c_id, level_n),
                    )
                    if conn.total_changes > before_changes:
                        ins += 1
                    else:
                        cur = conn.execute(
                            "SELECT expected_level FROM role_competencies WHERE role_id=? AND competency_id=?",
                            (r_id, c_id),
                        ).fetchone()
                        if cur and cur["expected_level"] != level_n:
                            conn.execute(
                                "UPDATE role_competencies SET expected_level=? WHERE role_id=? AND competency_id=?",
                                (level_n, r_id, c_id),
                            )
                            upd += 1
    return (ins, upd)

def ingest_role_adjacency(adjacency_json: Any, conn: sqlite3.Connection) -> Tuple[int, int]:
    """Upsert role_adjacency.

    Supports:
    - List of dicts {from_role, to_role, overlap_pct}
    - Matrix form with { roles: [...], overlaps: [[pct,..], ...] }

    Returns: (inserted, updated) counts.
    """
    if not adjacency_json:
        return (0, 0)
    ins = 0
    upd = 0
    with conn:
        # Explicit edges
        if isinstance(adjacency_json, list):
            for item in adjacency_json:
                from_name = normalize_name(item.get("from_role") or item.get("from"))
                to_name = normalize_name(item.get("to_role") or item.get("to"))
                try:
                    overlap = float(item.get("overlap_pct"))
                except Exception:
                    overlap = None
                if not from_name or not to_name or overlap is None:
                    continue
                fr = _get_role_id(conn, from_name)
                to = _get_role_id(conn, to_name)
                if not fr or not to:
                    continue
                before_changes = conn.total_changes
                conn.execute(
                    "INSERT OR IGNORE INTO role_adjacency(from_role_id, to_role_id, overlap_pct) VALUES (?,?,?)",
                    (fr, to, overlap),
                )
                if conn.total_changes > before_changes:
                    ins += 1
                else:
                    cur = conn.execute(
                        "SELECT overlap_pct FROM role_adjacency WHERE from_role_id=? AND to_role_id=?",
                        (fr, to),
                    ).fetchone()
                    if cur and float(cur["overlap_pct"]) != overlap:
                        conn.execute(
                            "UPDATE role_adjacency SET overlap_pct=? WHERE from_role_id=? AND to_role_id=?",
                            (overlap, fr, to),
                        )
                        upd += 1
        # Matrix
        elif isinstance(adjacency_json, dict):
            roles = [normalize_name(x) for x in (adjacency_json.get("roles") or [])]
            overlaps = adjacency_json.get("overlaps") or []
            for i, row in enumerate(overlaps):
                from_name = roles[i] if i < len(roles) else None
                if not from_name:
                    continue
                fr = _get_role_id(conn, from_name)
                if not fr:
                    continue
                for j, pct in enumerate(row):
                    to_name = roles[j] if j < len(roles) else None
                    if to_name is None:
                        continue
                    try:
                        overlap = float(pct)
                    except Exception:
                        continue
                    to = _get_role_id(conn, to_name)
                    if not to:
                        continue
                    before_changes = conn.total_changes
                    conn.execute(
                        "INSERT OR IGNORE INTO role_adjacency(from_role_id, to_role_id, overlap_pct) VALUES (?,?,?)",
                        (fr, to, overlap),
                    )
                    if conn.total_changes > before_changes:
                        ins += 1
                    else:
                        cur = conn.execute(
                            "SELECT overlap_pct FROM role_adjacency WHERE from_role_id=? AND to_role_id=?",
                            (fr, to),
                        ).fetchone()
                        if cur and float(cur["overlap_pct"]) != overlap:
                            conn.execute(
                                "UPDATE role_adjacency SET overlap_pct=? WHERE from_role_id=? AND to_role_id=?",
                                (overlap, fr, to),
                            )
                            upd += 1
    return (ins, upd)

def _count_table(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    return int(row["c"]) if row else 0

def _print_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    counts = {
        "roles": _count_table(conn, "roles"),
        "competencies": _count_table(conn, "competencies"),
        "role_competencies": _count_table(conn, "role_competencies"),
        "role_adjacency": _count_table(conn, "role_adjacency"),
        "resources": _count_table(conn, "resources"),
    }
    print("\nRow counts after ingestion:")
    for k, v in counts.items():
        print(f"- {k}: {v}")
    return counts

def _write_summary(counts: Dict[str, int], path: str = "ingestion_summary.txt") -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("Career Navigator DB Ingestion Summary\n")
            f.write("=====================================\n")
            for k, v in counts.items():
                f.write(f"{k}: {v}\n")
        print(f"\nSummary written to {path}")
    except Exception as e:
        print(f"Warning: could not write summary file: {e}")

# PUBLIC_INTERFACE
def main() -> None:
    """Run JSON ingestion into SQLite with verification output.

    Environment:
    - BACKEND_DATA_DIR: optional override for backend data directory
    """
    explicit_backend_dir = os.environ.get("BACKEND_DATA_DIR")

    # Prefer explicit path, else use the request's absolute default if present, else fall back to sibling path.
    request_default = "/home/kavia/workspace/code-generation/career-path-navigator-41368-41378/career_navigator_backend/data"
    data_dir = explicit_backend_dir or (request_default if os.path.isdir(request_default) else DEFAULT_DATA_DIR)

    print(f"Using data directory: {data_dir}")
    if not os.path.isdir(data_dir):
        print("No data directory found. Skipping ingestion.")
        return

    # Known dataset file names
    roles_file = os.path.join(data_dir, "roles.json")
    comp_defs_file = os.path.join(data_dir, "competencies_definitions.json")
    res_file = os.path.join(data_dir, "resources.json")
    role_comp_file = os.path.join(data_dir, "competencies_matrix.json")  # optional
    # adjacency variants
    adj_vs_ca_file = os.path.join(data_dir, "adjacency_vs_ca.json")      # optional
    adj_matrix_file = os.path.join(data_dir, "adjacency_matrix.json")    # optional

    with closing(_ensure_conn()) as conn:
        # Load datasets
        roles = _safe_load_json(roles_file)
        comp_defs = _safe_load_json(comp_defs_file)
        resources = _safe_load_json(res_file)
        role_comp = _safe_load_json(role_comp_file)

        # Adjacency: accept either list or matrix variants
        adj_data = None
        for p in [adj_vs_ca_file, adj_matrix_file]:
            tmp = _safe_load_json(p)
            if tmp is not None:
                adj_data = tmp
                break

        # Ingest base catalogs
        total_roles = ingest_roles(roles if isinstance(roles, list) else [], conn)
        total_comp = ingest_competencies(comp_defs if isinstance(comp_defs, list) else [], conn)
        total_res = ingest_resources(resources if isinstance(resources, list) else [], conn)

        # Ingest relationships
        rc_ins = rc_upd = 0
        if role_comp is not None:
            rc_ins, rc_upd = ingest_role_competencies(role_comp, conn)

        adj_ins = adj_upd = 0
        if adj_data is not None:
            adj_ins, adj_upd = ingest_role_adjacency(adj_data, conn)

        print("\nIngestion operations summary:")
        print(f"- roles inserted: {total_roles}")
        print(f"- competencies inserted: {total_comp}")
        print(f"- resources inserted: {total_res}")
        print(f"- role_competencies inserted/updated: {rc_ins}/{rc_upd}")
        print(f"- role_adjacency inserted/updated: {adj_ins}/{adj_upd}")

        # Verify and print counts
        counts = _print_counts(conn)

        # Also emit verification SELECTs to stdout for the visualizer confirmation
        for table in ["roles", "competencies", "role_competencies", "role_adjacency", "resources"]:
            row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            print(f"SELECT COUNT(*) FROM {table} -> {int(row['c'])}")

        # Write summary file
        _write_summary(counts)

    print("\nIngestion complete. You can verify in the SQLite visualizer.")

if __name__ == "__main__":
    main()
