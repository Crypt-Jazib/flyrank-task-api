import sqlite3
from pathlib import Path
from fastapi import FastAPI, Request, Response
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

app = FastAPI(
    title="Task API",
    version="2.0",
    description="A RESTful CRUD API backed by a persistent SQLite database."
)

@app.get("/", description="API overview and available endpoints.")
def read_root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}

@app.get("/health", description="Health check endpoint.")
def health_check():
    return {"status": "ok"}

@app.get("/tasks", description="Retrieve all tasks from SQLite.")
def get_tasks():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks").fetchall()
        return [row_to_dict(row) for row in rows]

@app.get("/tasks/{task_id}", description="Retrieve a single task by ID from SQLite.")
def get_task(task_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return row_to_dict(row)

@app.post("/tasks", status_code=201, description="Create a new task in SQLite.")
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

@app.put("/tasks/{task_id}", description="Update an existing task in SQLite.")
async def update_task(task_id: int, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict) or not body:
        return JSONResponse(status_code=400, content={"error": "Request body cannot be empty"})

    if "title" not in body and "done" not in body:
        return JSONResponse(status_code=400, content={"error": "Provide 'title' and/or 'done' to update"})

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if not existing:
            return JSONResponse(status_code=404, content={"error": "Task not found"})

        new_title = existing["title"]
        new_done = bool(existing["done"])

        if "title" in body:
            if not isinstance(body["title"], str) or not body["title"].strip():
                return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
            new_title = body["title"].strip()

        if "done" in body:
            if not isinstance(body["done"], bool):
                return JSONResponse(status_code=400, content={"error": "'done' must be a boolean (true or false)"})
            new_done = body["done"]

        conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (new_title, new_done, task_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return row_to_dict(updated)

@app.delete("/tasks/{task_id}", status_code=204, description="Delete a task from SQLite.")
def delete_task(task_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return Response(status_code=204)