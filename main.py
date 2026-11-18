import sqlite3
from pathlib import Path
from fastapi import FastAPI

DB_PATH = Path(__file__).resolve().parent / "tasks.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Learn FastAPI", True),
                    ("Build a CRUD API", False),
                    ("Connect SQLite database", False),
                ],
            )
        conn.commit()

init_db()

app = FastAPI(title="Task API", version="2.0", description="CRUD API backed by SQLite.")

@app.get("/")
def read_root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health_check():
    return {"status": "ok"}