import sqlite3
from typing import Optional
from fastapi import FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

DATABASE = "tasks.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", ("Buy groceries", 0))
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", ("Read a book", 1))
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", ("Write code", 0))
        conn.commit()
    conn.close()


app = FastAPI(
    title="Task Management API",
    description="A lightweight SQLite-backed CRUD API for managing to-do tasks.",
    version="2.0.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid request body or parameters"},
    )


class TaskCreate(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v is not None else None


@app.get(
    "/",
    summary="API Root Information",
    description="Returns API metadata and primary endpoints.",
)
def read_root():
    return {
        "name": "Task API",
        "version": "2.0",
        "endpoints": ["/tasks"],
    }


@app.get(
    "/health",
    summary="Service Health Check",
    description="Returns the health status of the API server.",
)
def read_health():
    return {"status": "ok"}


@app.get(
    "/tasks",
    summary="List all tasks",
    description="Returns tasks from the SQLite database.",
)
def get_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "title": row["title"], "done": bool(row["done"])} for row in rows]


@app.get(
    "/tasks/{id}",
    summary="Get a single task",
    description="Fetches a specific task from SQLite by ID. Returns 404 if not found.",
)
def get_task(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Task not found"},
        )
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
