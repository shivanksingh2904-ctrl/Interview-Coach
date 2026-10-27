# Interview Coach

Practice interviews with AI scoring (clarity, structure, relevance, depth, confidence), voice input, and a progress dashboard.
FastAPI + SQLAlchemy + JWT auth + Anthropic API. One service serves both the API (`/api/*`) and the web UI (`/`).

## Run locally
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then edit; or just export the variables
export ANTHROPIC_API_KEY=sk-ant-...                    # optional: without it, the app runs in demo mode
uvicorn app.main:app --reload
```
Open http://localhost:8000 (API docs at /docs). Run tests: `pytest`.

## Deploy on Render (free)
1. Push this folder to a GitHub repo.
2. Render dashboard > New > Blueprint > pick the repo. It reads `render.yaml`, creates the web service and a Postgres database.
3. When asked, paste your `ANTHROPIC_API_KEY`. `SECRET_KEY` is generated for you.
4. Wait for the build, then open the `onrender.com` URL. `/api/health` should return `{"ok":true}`.
