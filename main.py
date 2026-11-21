import os
import secrets
import sqlite3
from contextlib import contextmanager
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# 1. Configuration (read from environment variables, with safe defaults
DB_PATH = os.getenv("DB_PATH", "tasks.db")
API_KEY = os.getenv("API_KEY", "my-secret-key")  # change this in real use!

# 2. Database helpers (SQLite)
@contextmanager
def get_db():
    """Open a DB connection, commit on success, always close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the tasks table if it does not exist yet."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT,
                priority    TEXT    NOT NULL DEFAULT 'medium',
                completed   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
def row_to_task(row: sqlite3.Row) -> dict:
    """Convert a DB row into a dict (SQLite stores booleans as 0/1)."""
    task = dict(row)
    task["completed"] = bool(task["completed"])
    return task

init_db()

# 3. Schemas (Pydantic) - request/response validation
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, examples=["Finish Module 05"])
    description: Optional[str] = Field(None, max_length=500, examples=["Build REST API"])
    priority: Literal["low", "medium", "high"] = "medium"
    completed: bool = False


class TaskUpdate(BaseModel):
    """All fields optional - used for partial updates (PATCH)."""

    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: Optional[Literal["low", "medium", "high"]] = None
    completed: Optional[bool] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: str
    completed: bool
    created_at: str

# 4. Authentication (API key)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(key: Optional[str] = Security(api_key_header)) -> None:
    """Reject the request with 401 if the key is missing or wrong."""
    if key is None or not secrets.compare_digest(key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

# 5. App + routes
app = FastAPI(
    title="Task Manager API",
    description="A simple REST API with SQLite storage, CRUD operations, "
    "API-key authentication and schema validation.",
    version="1.0.0",
)

# every route in this router requires a valid API key
router = APIRouter(prefix="/tasks", tags=["Tasks"], dependencies=[Depends(verify_api_key)])

@app.get("/", tags=["Health"])
def health_check():
    """Public endpoint - no authentication needed."""
    return {"status": "ok", "message": "Task Manager API is running"}

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    """CREATE - add a new task."""
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, priority, completed) VALUES (?, ?, ?, ?)",
            (task.title, task.description, task.priority, int(task.completed)),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_task(row)

@router.get("", response_model=List[TaskOut])
def list_tasks(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[Literal["low", "medium", "high"]] = Query(None),
    limit: int = Query(10, ge=1, le=100, description="Max items to return"),
    skip: int = Query(0, ge=0, description="Items to skip (pagination)"),
):
    """READ - list tasks with optional filters and pagination."""
    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if completed is not None:
        query += " AND completed = ?"
        params.append(int(completed))
    if priority is not None:
        query += " AND priority = ?"
        params.append(priority)
    query += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, skip]

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row_to_task(r) for r in rows]

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int):
    """READ - get one task by id."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return row_to_task(row)

@router.put("/{task_id}", response_model=TaskOut)
def replace_task(task_id: int, task: TaskCreate):
    """UPDATE - replace the whole task."""
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE tasks SET title = ?, description = ?, priority = ?, completed = ? WHERE id = ?",
            (task.title, task.description, task.priority, int(task.completed), task_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, changes: TaskUpdate):
    """UPDATE - change only the fields that were sent."""
    data = changes.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    # column names come from our own model, never from the user -> safe
    set_clause = ", ".join(f"{col} = ?" for col in data)
    values = [int(v) if isinstance(v, bool) else v for v in data.values()]

    with get_db() as conn:
        cur = conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", (*values, task_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    """DELETE - remove a task."""
    with get_db() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")

app.include_router(router)
