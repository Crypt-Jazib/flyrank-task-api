import sqlite3
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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

def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),
    }

init_db()

app = FastAPI(title="Task API", version="2.0", description="CRUD API backed by SQLite.")

@app.get("/")
def read_root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/tasks", description="List all tasks from SQLite.")
def get_tasks():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks").fetchall()
        return [row_to_dict(row) for row in rows]

@app.get("/tasks/{task_id}", description="Get a single task by ID from SQLite.")
def get_task(task_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return row_to_dict(row)

@app.post("/tasks", status_code=201, description="Insert a new task into SQLite.")
async def create_task(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})

    clean_title = title.strip()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (clean_title, False),
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (new_id,)
        ).fetchone()
        return row_to_dict(row)