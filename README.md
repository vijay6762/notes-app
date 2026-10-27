# 📝 Notes App: FastAPI + Streamlit + Postgres

A full-stack notes app. Users sign up, log in, and create, edit and delete their own private notes.
It has a **FastAPI** REST backend with JWT authentication, a **Streamlit** web frontend, and a
**Postgres** database. It is deployed for free on **Render** and **Neon**.

## 🔗 Live demo

| | Link |
|---|---|
| App (frontend) | https://notes-frontend-4ub5.onrender.com |
| API docs (Swagger) | https://notes-api-0bc6.onrender.com/docs |
| Health check | https://notes-api-0bc6.onrender.com/health |

> Free hosting sleeps when idle. The first visit can take ~50 seconds to wake up.

## ✨ Features

- User registration and login with **JWT bearer tokens** (tokens expire after 60 minutes)
- Passwords hashed with **Argon2** (via `pwdlib`), never stored in plain text
- Full **CRUD** for notes: create, list, view, update (partial PATCH) and delete
- **Per-user isolation**: users can only see and change their own notes (others get `404`)
- Input validation with **SQLModel / Pydantic** (title length, username and password length)
- Streamlit UI with login/register tabs, an add-note form, and editable notes you can expand
- Automated tests with **pytest**, run against an in-memory SQLite database

## 🏗️ Architecture

```
Browser
   │
   ▼
Streamlit frontend      (Render web service)   frontend/app.py
   │  HTTP + JSON, Bearer token      ← API_URL
   ▼
FastAPI backend         (Render web service)   main.py
   │  SQL via SQLModel / SQLAlchemy  ← DATABASE_URL
   ▼
Postgres database       (Neon)                 tables: user, note
```

- **GitHub** stores the code. Render redeploys automatically on every push to `main`.
- **Render** runs the two Python web services. Its disk is temporary, so no data is kept there.
- **Neon** hosts the Postgres database, so users and notes survive restarts and redeploys.
- Locally, the backend falls back to a SQLite file (`notes.db`) when `DATABASE_URL` is not set.

## 🧰 Tech stack

| Layer | Tools |
|---|---|
| Backend | FastAPI, Uvicorn, SQLModel (SQLAlchemy + Pydantic), PyJWT, pwdlib[argon2] |
| Frontend | Streamlit, requests |
| Database | Postgres on Neon (production), SQLite (local), psycopg 3 driver |
| Testing | pytest, FastAPI TestClient |
| Hosting | Render (Blueprint via `render.yaml`), Neon |

## 📁 Project structure

```
notes_api/
├── main.py                  # FastAPI app: models, auth, notes endpoints
├── test_main.py             # pytest tests
├── requirements.txt         # backend dependencies
├── frontend/
│   ├── app.py               # Streamlit frontend
│   └── requirements.txt     # frontend dependencies
├── render.yaml              # Render Blueprint (deploys both services)
├── .gitignore
└── README.md
```

## 📡 API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | – | Health check, returns `{"status": "ok"}` |
| POST | `/register` | – | Create a user (`username` 3–30 chars, `password` min 8) |
| POST | `/login` | – | Form fields `username`, `password`. Returns `access_token` |
| GET | `/me` | ✅ | The logged-in user |
| POST | `/notes` | ✅ | Create a note (`title` 1–100 chars, `content`) |
| GET | `/notes` | ✅ | List your notes |
| GET | `/notes/{id}` | ✅ | Get one note |
| PATCH | `/notes/{id}` | ✅ | Update `title` and/or `content` |
| DELETE | `/notes/{id}` | ✅ | Delete a note |

Authenticated requests send the header `Authorization: Bearer <access_token>`.
You can try every endpoint interactively at `/docs`.

## 💻 Run locally

**1. Set up** (Windows PowerShell):

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt -r frontend/requirements.txt pytest
```

**2. Start the backend** (terminal 1). Docs at http://127.0.0.1:8000/docs:

```bash
uvicorn main:app --reload
```

**3. Start the frontend** (terminal 2). Opens http://localhost:8501:

```bash
streamlit run frontend/app.py
```

Locally, data is saved in `notes.db`. That file is separate from the live Neon database.

**4. Run the tests:**

```bash
pytest -q
```

## ⚙️ Environment variables

| Variable | Used by | Purpose | Local default |
|---|---|---|---|
| `DATABASE_URL` | backend | Postgres connection string (from Neon) | `sqlite:///notes.db` |
| `SECRET_KEY` | backend | Signs JWT tokens. Keep it secret | a dev placeholder |
| `API_URL` | frontend | Where the backend lives | `http://127.0.0.1:8000` |

Never commit real values. Set them in the Render dashboard.

## 🚀 Deployment (free)

1. **GitHub:** push this project to a repository.
2. **Neon:** create a project at [neon.tech](https://neon.tech) in the same region as Render
   (Render's default is Oregon, so pick *AWS US West 2*). Copy the connection string.
3. **Render:** go to **New → Blueprint** and select the repo. Render reads `render.yaml` and creates:
   - `notes-api`: set `DATABASE_URL` to the Neon string. `SECRET_KEY` is generated for you.
   - `notes-frontend`: set `API_URL` to the `notes-api` URL once it is live.
4. Open the frontend URL, register and add a note. The `user` and `note` tables show up in Neon → **Tables**.

Pushing to `main` redeploys both services automatically.

## 🧪 Tests

`test_main.py` covers:

- the full happy path: register → login → create → list → update → delete
- requests without a valid token are rejected with `401`
- one user cannot read, edit or delete another user's note

## 📚 What I learned

- Building a REST API with FastAPI, dependency injection and SQLModel
- Password hashing and JWT authentication
- Writing isolated tests with dependency overrides and an in-memory database
- Connecting a Streamlit frontend to a separate backend over HTTP
- Deploying a multi-service app with environment variables and a managed Postgres database
