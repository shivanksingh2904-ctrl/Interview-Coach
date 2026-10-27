import os
import tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")
os.environ.pop("ANTHROPIC_API_KEY", None)
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

c = TestClient(app)


def test_full_flow():
    r = c.post("/api/register", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    h = {"Authorization": "Bearer " + r.json()["token"]}
    s = c.post("/api/sessions", json={"role": "Backend Developer", "kind": "behavioral",
                                       "difficulty": "easy", "count": 2}, headers=h).json()
    assert len(s["questions"]) == 2
    q = c.post(f"/api/questions/{s['questions'][0]['id']}/answer",
               json={"answer": "word " * 80, "seconds": 30}, headers=h).json()
    assert 1 <= q["clarity"] <= 10
    assert c.get("/api/analytics", headers=h).json()["answered"] == 1
    assert c.post("/api/login", json={"email": "a@b.com", "password": "wrongpass1"}).status_code == 401


def test_requires_auth():
    assert c.get("/api/sessions").status_code in (401, 403)
