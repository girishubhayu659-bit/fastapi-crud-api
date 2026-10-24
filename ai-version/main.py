import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Task API - AI Version")


def get_db():
    conn = sqlite3.connect("tasks.db")
    return conn


@app.on_event("startup")
def setup_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            done INTEGER
        )
    """)
    # Naive AI seed without checking count==0 can cause duplicate seeds
    conn.commit()
    conn.close()


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


@app.get("/tasks")
def read_tasks():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title, done FROM tasks")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in rows]


@app.get("/tasks/{task_id}")
def read_task(task_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": row[0], "title": row[1], "done": bool(row[2])}


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, done) VALUES (?, 0)", (task.title,))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return {"id": new_id, "title": task.title, "done": False}


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (task.title, int(task.done or 0), task_id))
    conn.commit()
    conn.close()
    return {"id": task_id, "title": task.title, "done": task.done}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    # Naive AI returns 200 with JSON message instead of 204 No Content
    return {"message": "deleted"}
