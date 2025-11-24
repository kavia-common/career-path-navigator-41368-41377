# Career Navigator Database Schema

This folder contains the SQLite schema and helpers for the Career Path Navigator MVP.

Files:
- schema.sql: Authoritative schema (idempotent).
- init_db.py: Initializes myapp.db, applies schema, seeds minimal data, and writes sqlite.env for the visualizer.
- ingest_json.py: Ingests JSON data from the backend data folder and upserts into roles, competencies, role_competencies, role_adjacency, and resources. Supports CLI flags for explicit paths.
- compat_views.sql: Optional compatibility views and verification SQL.
- test_db.py: Smoke tests for schema, indices, and foreign key enforcement.

Quickstart:
1) Initialize DB
   python3 init_db.py

2) Ingest JSON from backend datasets (idempotent)
   # Recommended explicit invocation to avoid path ambiguity:
   python3 ingest_json.py \
     --db-path /home/kavia/workspace/code-generation/career-path-navigator-41368-41377/career_navigator_database/myapp.db \
     --data-dir /home/kavia/workspace/code-generation/career-path-navigator-41368-41378/career_navigator_backend/data \
     --create-views

   # Alternatively via environment variable (legacy):
   BACKEND_DATA_DIR=/home/kavia/workspace/code-generation/career-path-navigator-41368-41378/career_navigator_backend/data python3 ingest_json.py

   On completion, it prints SELECT count(*) for:
   - roles, competencies, role_competencies, role_adjacency, resources
   and writes ingestion_summary.txt with row counts.

   Manual verification queries (e.g., via db_shell.py or sqlite3):
   SELECT COUNT(*) FROM roles;
   SELECT COUNT(*) FROM competencies;
   SELECT COUNT(*) FROM role_competencies;
   SELECT COUNT(*) FROM role_adjacency;
   SELECT COUNT(*) FROM resources;

3) Run smoke tests
   python3 test_db.py

Viewer:
- Source environment for the simple DB viewer (points to absolute DB path):
  source db_visualizer/sqlite.env

Re-run ingestion later:
- If datasets change, simply run:
  python3 ingest_json.py \
    --db-path /home/kavia/workspace/code-generation/career-path-navigator-41368-41377/career_navigator_database/myapp.db \
    --data-dir /home/kavia/workspace/code-generation/career-path-navigator-41368-41378/career_navigator_backend/data
- Then refresh the SQLite visualizer and confirm counts match the printed summary.
