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
        cursor.execute("SELECT id, title, done FROM tasks ORDER BY id ASC;")
        rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "title": row["title"], "done": bool(row["done"])} for row in rows]


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
