import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/tasks.db")
INIT_SQL_PATH = Path(__file__).resolve().parent / "init.sql"


class TaskRepository:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        sql_script = INIT_SQL_PATH.read_text(encoding="utf-8")
        with self._get_conn() as conn:
            conn.executescript(sql_script)
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "done": bool(row["done"]),
        }

    def list_tasks(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, title, done FROM tasks ORDER BY id ASC"
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_task(self, task_id: int) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def create_task(self, title: str) -> dict:
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                (title, False),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            return self._row_to_dict(row)

    def update_task(self, task_id: int, title: str | None = None, done: bool | None = None) -> dict | None:
        existing = self.get_task(task_id)
        if not existing:
            return None

        new_title = title if title is not None else existing["title"]
        new_done = done if done is not None else existing["done"]

        with self._get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
                (new_title, new_done, task_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def delete_task(self, task_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0