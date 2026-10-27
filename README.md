# Notes API + Streamlit frontend

FastAPI backend (users, JWT login, notes CRUD) with a Streamlit UI that calls it over HTTP.

```
main.py              FastAPI backend
test_main.py         pytest tests
requirements.txt     backend dependencies
frontend/app.py      Streamlit frontend
frontend/requirements.txt
render.yaml          one-click deploy of both on Render
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r frontend/requirements.txt pytest
```

Terminal 1 (backend, docs at http://127.0.0.1:8000/docs):

```bash
uvicorn main:app --reload
```

Terminal 2 (frontend, opens http://localhost:8501):

```bash
streamlit run frontend/app.py
```

## Deploy (free)

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Notes API with Streamlit frontend"
git branch -M main
git remote add origin https://github.com/<you>/notes-app.git
git push -u origin main
```

### 2. Database (recommended)

Render's disk is wiped on every redeploy/restart, so SQLite loses data there.
Create a free Postgres database at https://neon.tech and copy its connection string
(`postgresql://...`). The app converts it to the right driver automatically.

### 3. Deploy on Render

1. https://render.com -> **New -> Blueprint** -> select the repo. It reads `render.yaml`.
2. When asked, set `DATABASE_URL` to the Neon string. Leave `API_URL` empty for now.
3. After deploy, open the **notes-api** service and copy its URL
   (e.g. `https://notes-api-xxxx.onrender.com`). Check `<url>/health` returns `{"status":"ok"}`.
4. Open **notes-frontend -> Environment**, set `API_URL` to that URL, save (it redeploys).
5. Open the notes-frontend URL. Register, log in, add notes.

Free Render services sleep after ~15 min idle; the first request then takes ~50 s.

### Alternative: frontend on Streamlit Community Cloud

1. https://share.streamlit.io -> **Create app** -> pick the repo, branch `main`,
   main file `frontend/app.py`.
2. **Advanced settings -> Secrets**:
   ```toml
   API_URL = "https://notes-api-xxxx.onrender.com"
   ```
3. Deploy. (You can then delete the notes-frontend service on Render.)
