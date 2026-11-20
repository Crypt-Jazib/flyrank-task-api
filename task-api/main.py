from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from repository import TaskRepository

app = FastAPI(
    title="Task API",
    version="3.0",
    description="Layered CRUD API containerized with Docker and persistent SQLite volume."
)

repo = TaskRepository()


@app.get("/", description="API overview and available endpoints.")
def read_root():
    return {"name": "Task API", "version": "3.0", "endpoints": ["/tasks"]}


@app.get("/health", description="Health check endpoint.")
def health_check():
    return {"status": "ok"}


@app.get("/tasks", description="Retrieve all tasks.")
def get_tasks():
    return repo.list_tasks()


@app.get("/tasks/{task_id}", description="Retrieve a single task by ID.")
def get_task(task_id: int):
    task = repo.get_task(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return task


@app.post("/tasks", status_code=201, description="Create a new task.")
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

    return repo.create_task(title.strip())


@app.put("/tasks/{task_id}", description="Update an existing task.")
async def update_task(task_id: int, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict) or not body:
        return JSONResponse(status_code=400, content={"error": "Request body cannot be empty"})

    if "title" not in body and "done" not in body:
        return JSONResponse(status_code=400, content={"error": "Provide 'title' and/or 'done' to update"})

    new_title = None
    if "title" in body:
        if not isinstance(body["title"], str) or not body["title"].strip():
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        new_title = body["title"].strip()

    new_done = None
    if "done" in body:
        if not isinstance(body["done"], bool):
            return JSONResponse(status_code=400, content={"error": "'done' must be a boolean (true or false)"})
        new_done = body["done"]

    updated = repo.update_task(task_id, title=new_title, done=new_done)
    if not updated:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return updated


@app.delete("/tasks/{task_id}", status_code=204, description="Delete a task.")
def delete_task(task_id: int):
    deleted = repo.delete_task(task_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return Response(status_code=204)