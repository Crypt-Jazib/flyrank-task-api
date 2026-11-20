# Task API — Containerized Layered Edition

A RESTful CRUD API for managing a persistent to-do list, built with Python, FastAPI, SQLite, and Docker Compose.

## Architecture & Layering
- **Separation of concerns:** All database queries and schema initialization live in `repository.py` (`TaskRepository`), while `main.py` handles HTTP routing and request validation. Swapping the storage backend required zero changes to the API routes or service logic.
- **Configuration via `.env`:** The database file path (`DATABASE_PATH`) is loaded from `.env` (gitignored), with `.env.example` committed as a template.
- **Schema initialization:** On startup, `TaskRepository` executes `init.sql` to create the `tasks` table and seed initial rows if empty.

## How to Run with Docker Compose

1. Copy the environment template:
   ```bash
   cp .env.example .env