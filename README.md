# Task Manager REST API

A fully documented REST API built with **FastAPI** and **SQLite** as part of *Module 05 – Python Application Development*.
It supports complete CRUD operations, API-key authentication, request validation and automated tests.

## Features

- Full CRUD for tasks (Create, Read, Update, Delete)
- SQLite database storage using Python's built-in `sqlite3` (parameterised queries, safe from SQL injection)
- API-key authentication using the `X-API-Key` header
- Schema validation with Pydantic (automatic `422` errors on bad input)
- Filtering and pagination on the list endpoint
- Auto-generated interactive docs (Swagger UI and ReDoc)
- Automated endpoint tests with `pytest`

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.9+ | Language |
| FastAPI | Web framework |
| Uvicorn | ASGI server |
| SQLite | Database |
| Pydantic | Schema validation |
| Pytest + HTTPX | Testing |

## Project Structure

```
task-manager-api/
├── main.py            # API code (routes, DB, auth, schemas)
├── test.py            # Automated tests
├── README.md          # Documentation
├── .gitignore         # Files Git should ignore
└── tasks.db           # SQLite DB (auto-created on first run)
```

## Setup & Installation

```bash
# 1. Clone the repo
git clone https://github.com/nehakhatrii312/task-manager-api.git
cd task-manager-api

# 2. (Optional) create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Run the server
python -m uvicorn main:app --reload
```

The API runs at **http://127.0.0.1:8000**
Interactive docs: **http://127.0.0.1:8000/docs**

### Environment variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `my-secret-key` | Key clients must send in `X-API-Key` |
| `DB_PATH` | `tasks.db` | SQLite file location |

Windows (CMD): `set API_KEY=mynewkey` · PowerShell: `$env:API_KEY="mynewkey"` · macOS/Linux: `export API_KEY=mynewkey`

## Authentication

Every `/tasks` endpoint needs this header:

```
X-API-Key: my-secret-key
```

Missing or wrong key → `401 Unauthorized`.
In Swagger UI, click **Authorize** and paste the key once.

## API Endpoints

| Method | Endpoint | Description | Success |
|--------|----------|-------------|---------|
| GET | `/` | Health check (public) | 200 |
| POST | `/tasks` | Create a task | 201 |
| GET | `/tasks` | List tasks (filters + pagination) | 200 |
| GET | `/tasks/{id}` | Get one task | 200 |
| PUT | `/tasks/{id}` | Replace a task | 200 |
| PATCH | `/tasks/{id}` | Partially update a task | 200 |
| DELETE | `/tasks/{id}` | Delete a task | 204 |

**Query params for `GET /tasks`:** `completed` (true/false), `priority` (low/medium/high), `limit` (1–100, default 10), `skip` (default 0)

## Example Requests

**Create a task**

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{"title": "Finish Module 05", "description": "Build REST API", "priority": "high"}'
```

Response `201`:

```json
{
  "id": 1,
  "title": "Finish Module 05",
  "description": "Build REST API",
  "priority": "high",
  "completed": false,
  "created_at": "2026-11-21 08:30:00"
}
```

**List high-priority pending tasks**

```bash
curl "http://127.0.0.1:8000/tasks?priority=high&completed=false" -H "X-API-Key: my-secret-key"
```

**Mark a task as completed**

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{"completed": true}'
```

**Delete a task**

```bash
curl -X DELETE http://127.0.0.1:8000/tasks/1 -H "X-API-Key: my-secret-key"
```

## Validation Rules

| Field | Rule |
|-------|------|
| `title` | required, 1–100 characters |
| `description` | optional, max 500 characters |
| `priority` | one of `low`, `medium`, `high` (default `medium`) |
| `completed` | boolean (default `false`) |

## HTTP Status Codes Used

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Bad request (e.g., empty PATCH body) |
| 401 | Missing / invalid API key |
| 404 | Task not found |
| 422 | Validation error |

## Running Tests

```bash
python -m pytest test.py -v
```

The tests use a temporary database, so your real data is never changed.

## Future Improvements

- JWT-based login with user accounts
- Per-user tasks
- Docker support and deployment
- Alembic migrations / SQLAlchemy ORM

## Author

**Neha Khatri** – BCA Student | Aspiring Full Stack Developer
Built as part of the Codomax Digital Solutions internship.
