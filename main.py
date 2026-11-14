from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A simple in-memory CRUD API for managing a to-do list."
)

tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": True},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Push project to GitHub", "done": False},
]

@app.get("/", description="API overview and available endpoints.")
def read_root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health", description="Health check endpoint.")
def health_check():
    return {"status": "ok"}

@app.get("/tasks", description="List all tasks in memory.")
def get_tasks():
    return tasks

@app.get("/tasks/{task_id}", description="Retrieve a single task by ID.")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

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

    next_id = max((t["id"] for t in tasks), default=0) + 1
    new_task = {"id": next_id, "title": title.strip(), "done": False}
    tasks.append(new_task)
    return new_task

@app.put("/tasks/{task_id}", description="Update an existing task's title and/or done status.")
async def update_task(task_id: int, request: Request):
    target_task = next((t for t in tasks if t["id"] == task_id), None)
    if not target_task:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict) or not body:
        return JSONResponse(status_code=400, content={"error": "Request body cannot be empty"})

    if "title" not in body and "done" not in body:
        return JSONResponse(status_code=400, content={"error": "Provide 'title' and/or 'done' to update"})

    if "title" in body:
        if not isinstance(body["title"], str) or not body["title"].strip():
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        target_task["title"] = body["title"].strip()

    if "done" in body:
        if not isinstance(body["done"], bool):
            return JSONResponse(status_code=400, content={"error": "'done' must be a boolean (true or false)"})
        target_task["done"] = body["done"]

    return target_task

@app.delete("/tasks/{task_id}", status_code=204, description="Delete a task by ID.")
def delete_task(task_id: int):
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(index)
            return Response(status_code=204)
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})