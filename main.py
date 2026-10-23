from typing import Optional
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid request body or parameters"},
    )


# In-memory storage with 3 initial example tasks
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read a book", "done": True},
    {"id": 3, "title": "Write code", "done": False},
]


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


@app.get("/")
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def read_health():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    return tasks


@app.get("/tasks/{id}")
def get_task(id: int):
    for task in tasks:
        if task["id"] == id:
            return task
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": f"Task {id} not found"},
    )


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate):
    next_id = max([t["id"] for t in tasks], default=0) + 1
    new_task = {
        "id": next_id,
        "title": task_in.title,
        "done": False,
    }
    tasks.append(new_task)
    return new_task


@app.put("/tasks/{id}")
def update_task(id: int, task_in: TaskUpdate):
    if task_in.title is None and task_in.done is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Request body must contain 'title' or 'done'"},
        )
    for task in tasks:
        if task["id"] == id:
            if task_in.title is not None:
                task["title"] = task_in.title
            if task_in.done is not None:
                task["done"] = task_in.done
            return task
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": f"Task {id} not found"},
    )


@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int):
    for i, task in enumerate(tasks):
        if task["id"] == id:
            tasks.pop(i)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": f"Task {id} not found"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
