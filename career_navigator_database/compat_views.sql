-- Compatibility views for alternate table naming, safe to run multiple times.
-- Currently no remaps needed; example left as comments.
-- CREATE VIEW IF NOT EXISTS role_adjacencies AS SELECT * FROM role_adjacency;

-- Verification queries (copy-paste in db_shell.py or any SQLite client)
-- SELECT COUNT(*) FROM roles;
-- SELECT COUNT(*) FROM competencies;
-- SELECT COUNT(*) FROM role_competencies;
-- SELECT COUNT(*) FROM role_adjacency;
-- SELECT COUNT(*) FROM resources;
