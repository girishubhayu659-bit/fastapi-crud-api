import os
import time
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
import psycopg
from psycopg.rows import dict_row

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://postgres:dev@localhost:5432/tasks")


def get_db_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db(max_retries=5, delay=2):
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        done BOOLEAN NOT NULL DEFAULT FALSE
                    );
                """)
                cursor.execute("SELECT COUNT(*) AS count FROM tasks;")
                row = cursor.fetchone()
                count = row["count"] if row else 0
                if count == 0:
                    cursor.execute(
                        "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                        ("Buy groceries", False),
                    )
                    cursor.execute(
                        "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                        ("Read a book", True),
                    )
                    cursor.execute(
                        "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                        ("Write code", False),
                    )
            conn.commit()
            conn.close()
            return
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                print(f"Database connection error: {e}")


app = FastAPI(
    title="Task Management API (Postgres Edition)",
    description="A containerized CRUD API backed by PostgreSQL.",
    version="3.0.0",
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
        "version": "3.0",
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
    description="Returns tasks from the PostgreSQL database.",
)
def get_tasks():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM tasks ORDER BY id ASC;")
        rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "title": row["title"], "done": bool(row["done"])} for row in rows]


@app.get(
    "/tasks/{id}",
    summary="Get a single task",
    description="Fetches a specific task from PostgreSQL by ID. Returns 404 if not found.",
)
def get_task(id: int):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM tasks WHERE id = %s;", (id,))
        row = cursor.fetchone()
    conn.close()
    if row is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Task not found"},
        )
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.post(
    "/tasks",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Inserts a new task into PostgreSQL with done=false.",
)
def create_task(task_in: TaskCreate):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done;",
            (task_in.title, False),
        )
        new_task = cursor.fetchone()
    conn.commit()
    conn.close()
    return {"id": new_task["id"], "title": new_task["title"], "done": bool(new_task["done"])}


@app.put(
    "/tasks/{id}",
    summary="Update an existing task",
    description="Updates task title and/or done status in PostgreSQL. Returns 404 if not found, 400 if invalid.",
)
def update_task(id: int, task_in: TaskUpdate):
    if task_in.title is None and task_in.done is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Request body must contain 'title' or 'done'"},
        )
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s;", (id,))
        existing = cursor.fetchone()
        if existing is None:
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Task not found"},
            )

        new_title = task_in.title if task_in.title is not None else existing["title"]
        new_done = task_in.done if task_in.done is not None else existing["done"]

        cursor.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done;",
            (new_title, new_done, id),
        )
        updated = cursor.fetchone()
    conn.commit()
    conn.close()
    return {"id": updated["id"], "title": updated["title"], "done": bool(updated["done"])}


@app.delete(
    "/tasks/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Removes a task from PostgreSQL by ID. Returns 204 on success, 404 if not found.",
)
def delete_task(id: int):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM tasks WHERE id = %s;", (id,))
        existing = cursor.fetchone()
        if existing is None:
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Task not found"},
            )
        cursor.execute("DELETE FROM tasks WHERE id = %s;", (id,))
    conn.commit()
    conn.close()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
