CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT 0
);

INSERT INTO tasks (title, done)
SELECT 'Learn FastAPI', 1
WHERE NOT EXISTS (SELECT 1 FROM tasks);

INSERT INTO tasks (title, done)
SELECT 'Containerize SQLite with Docker', 0
WHERE (SELECT COUNT(*) FROM tasks) = 1;

INSERT INTO tasks (title, done)
SELECT 'Verify persistence across container restarts', 0
WHERE (SELECT COUNT(*) FROM tasks) = 2;
