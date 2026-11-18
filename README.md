# Task API — SQLite Edition (W3 · A1)

A RESTful CRUD API for managing a persistent to-do list, built with Python, FastAPI, and SQLite.

## Why SQLite?
- **Zero-configuration persistence:** SQLite stores the entire database in a single local file without needing a separate database server process.
- **Data survives restarts:** Unlike Assignment 1's in-memory list, tasks are persisted to disk and remain intact when the server restarts.
- **Standard SQL:** Uses standard SQL queries (`SELECT`, `INSERT`, `UPDATE`, `DELETE`), making it easy to migrate to PostgreSQL or MySQL later.

## Database Storage Location
The SQLite database is automatically created on startup at `./tasks.db` (in the root directory alongside `main.py`). If `tasks.db` or the `tasks` table is missing, the app creates them and seeds 3 initial tasks only when the table is empty.

## How to Install & Run

```bash
pip install -r requirements.txt && uvicorn main:app --reload