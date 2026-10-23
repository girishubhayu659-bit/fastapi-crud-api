# Task Management CRUD API

A clean, lightweight RESTful CRUD API built with **Python 3.13** and **FastAPI**. It manages an in-memory to-do list supporting full Create, Read, Update, and Delete operations with interactive OpenAPI documentation via Swagger UI.

---

## 🚀 Quickstart (One Documented Command)

### 1. Prerequisites
- Python 3.10+ installed

### 2. Install & Run
Run the following single command to start the server:

```bash
python main.py
```

*(Alternatively, via Uvicorn CLI: `uvicorn main:app --reload --port 8000`)*

The server will boot on `http://localhost:8000`.

---

## 📖 API Documentation & Endpoints

Interactive Swagger UI documentation is available at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Endpoints Table

| Method | Endpoint | Description | Request Body | Success Status | Error Statuses |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | API root metadata and discovery | None | `200 OK` | — |
| `GET` | `/health` | Server health check | None | `200 OK` | — |
| `GET` | `/tasks` | List all tasks | None | `200 OK` | — |
| `GET` | `/tasks/{id}` | Retrieve a single task by ID | None | `200 OK` | `404 Not Found` |
| `POST` | `/tasks` | Create a new task (defaults `done: false`) | `{"title": "Buy milk"}` | `201 Created` | `400 Bad Request` |
| `PUT` | `/tasks/{id}` | Update task title and/or done status | `{"title": "Updated", "done": true}` | `200 OK` | `400 Bad Request`, `404 Not Found` |
| `DELETE`| `/tasks/{id}` | Delete a task by ID (returns empty body) | None | `204 No Content`| `404 Not Found` |

---

## 🔍 Sample `curl -i` Output

Real terminal output verifying headers and status codes:

### List All Tasks (`GET /tasks`)
```http
HTTP/1.1 200 OK
date: Fri, 23 Oct 2026 17:17:25 GMT
server: uvicorn
content-length: 133
content-type: application/json

[
  {"id": 1, "title": "Buy groceries", "done": false},
  {"id": 2, "title": "Read a book", "done": true},
  {"id": 3, "title": "Write code", "done": false}
]
```

### Create a Task (`POST /tasks`)
```http
HTTP/1.1 201 Created
date: Fri, 23 Oct 2026 17:13:18 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id": 4, "title": "Buy milk", "done": false}
```

### Validation Error on Missing/Empty Title (`POST /tasks`)
```http
HTTP/1.1 400 Bad Request
date: Fri, 23 Oct 2026 17:13:25 GMT
server: uvicorn
content-length: 66
content-type: application/json

{"error": "Invalid request: title is required and cannot be empty"}
```

### Not Found Error (`GET /tasks/99`)
```http
HTTP/1.1 404 Not Found
date: Fri, 23 Oct 2026 17:12:08 GMT
server: uvicorn
content-length: 29
content-type: application/json

{"error": "Task 99 not found"}
```

---

## 📸 Swagger UI Screenshot

Interactive documentation with "Try it out" capability for all routes:

![Swagger UI](swagger.png)

---

## 💡 The Mortality Experiment

When tasks are created or modified, they are stored exclusively in the process's working memory (`in-memory`). If the server restarts, all modifications are lost and reset to the initial state. This highlights why persistent storage mechanisms such as relational databases (e.g., PostgreSQL) are essential for production systems.
