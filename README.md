# Task Management CRUD API (Containerized PostgreSQL Stack)

A production-ready RESTful CRUD API built with **Python 3.11/3.13**, **FastAPI**, and a containerized **PostgreSQL** database managed via **Docker Compose**.

This assignment is the third evolution of the stack:
- **Assignment 1:** In-memory storage (volatile).
- **Assignment 2:** SQLite file storage (`tasks.db`).
- **Assignment 3 (This project):** Containerized PostgreSQL running as a standalone service with persistent Docker volumes and zero-leak environment configuration.

---

## 🚀 Quickstart (One Command for the Whole Stack)

### 1. Configure Secrets
Copy the committed environment template to create your local `.env`:

```bash
cp .env.example .env
```

*(On Windows PowerShell: `Copy-Item .env.example .env`)*

The `.env` file contains your connection string:
```text
DATABASE_URL=postgres://postgres:dev@localhost:5432/tasks
```
*(Inside the Docker Compose network, the host is automatically remapped to `db:5432`).*

### 2. Start the Entire Stack
Run the single command to build the app, launch PostgreSQL, provision tables, and seed initial tasks:

```bash
docker compose up
```

To run in the background (detached mode):
```bash
docker compose up -d
```

To stop the entire stack without losing data:
```bash
docker compose down
```

The API will be live at: **`http://localhost:8000`**  
Interactive Swagger UI documentation is available at: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🗄️ Database Verification (`psql`)

The PostgreSQL database runs in an isolated container with a named volume (`taskdata`) guaranteeing that records survive container lifecycle restarts. 

You can inspect the running table directly using `psql`:

![PostgreSQL psql verification](postgres_psql.png)

```bash
docker exec -it taskdb psql -U postgres -d tasks
```
```sql
\dt
SELECT id, title, done FROM tasks;
```

---

## 📖 API Documentation & Endpoints

| Method | Endpoint | Description | Request Body | Success Status | Error Statuses |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | API root metadata and discovery | None | `200 OK` | — |
| `GET` | `/health` | Server & DB health check (`SELECT 1`) | None | `200 OK` | `503 Service Unavailable` |
| `GET` | `/tasks` | List all tasks from PostgreSQL | None | `200 OK` | — |
| `GET` | `/tasks/{id}` | Retrieve a single task by ID | None | `200 OK` | `404 Not Found` |
| `POST` | `/tasks` | Create a new task (defaults `done: false`) | `{"title": "Buy milk"}` | `201 Created` | `400 Bad Request` |
| `PUT` | `/tasks/{id}` | Update task title and/or done status | `{"title": "Updated", "done": true}` | `200 OK` | `400 Bad Request`, `404 Not Found` |
| `DELETE`| `/tasks/{id}` | Delete a task by ID (returns empty body) | None | `204 No Content`| `404 Not Found` |

---

## 🔍 Sample `curl -i` Output

Real terminal output verifying status codes and PostgreSQL response:

### List All Tasks from Postgres (`GET /tasks`)
```http
HTTP/1.1 200 OK
date: Sun, 25 Oct 2026 14:48:10 GMT
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
date: Sun, 25 Oct 2026 14:48:22 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id": 4, "title": "Buy milk", "done": false}
```

### Validation Error (`POST /tasks`)
```http
HTTP/1.1 400 Bad Request
date: Sun, 25 Oct 2026 14:48:35 GMT
server: uvicorn
content-length: 46
content-type: application/json

{"error": "Invalid request body or parameters"}
```

### Delete Task (`DELETE /tasks/4`)
```http
HTTP/1.1 204 No Content
date: Sun, 25 Oct 2026 14:48:47 GMT
server: uvicorn
```

---

## 🛡️ Architecture & Security

1. **Zero Secret Leaks:** All database credentials are read from `.env`. The real `.env` is ignored by Git, while `.env.example` is committed as a reference.
2. **SQL Injection Defense:** All queries strictly use `%s` parameterized placeholders via `psycopg`.
3. **Data Persistence:** The `taskdata` volume mounts directly to `/var/lib/postgresql/data`. Running `docker compose down` and `docker compose up` preserves all rows.

