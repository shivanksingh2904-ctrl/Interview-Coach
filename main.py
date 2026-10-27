from pathlib import Path
from statistics import mean
from typing import Literal
from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from . import llm
from .auth import check_pw, current_user, get_db, hash_pw, make_token
from .db import Base, Interview, Question, User, engine

DIMS = llm.DIMS
Base.metadata.create_all(engine)
app = FastAPI(title="Interview Coach")


class Creds(BaseModel):
    email: str = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=100)


class NewSession(BaseModel):
    role: str = Field(min_length=2, max_length=80)
    kind: Literal["behavioral", "technical", "hr"]
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    count: int = Field(5, ge=1, le=10)


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=6000)
    seconds: int = Field(0, ge=0, le=3600)


def q_out(q: Question) -> dict:
    d = {"id": q.id, "text": q.text, "category": q.category, "answer": q.answer, "seconds": q.seconds,
         "feedback": q.feedback, "improved": q.improved}
    d.update({k: getattr(q, k) for k in DIMS})
    d["avg"] = round(mean(getattr(q, k) for k in DIMS), 1) if q.answer else None
    return d


def s_out(s: Interview, full: bool = True) -> dict:
    d = {"id": s.id, "role": s.role, "kind": s.kind, "difficulty": s.difficulty,
         "created_at": s.created_at.isoformat(), "overall": s.overall}
    if full:
        d["questions"] = [q_out(q) for q in s.questions]
    return d


def own(db, model, id_, user):
    obj = db.get(model, id_)
    owner = None if not obj else (obj.user_id if isinstance(obj, Interview) else obj.interview.user_id)
    if owner != user.id:
        raise HTTPException(404, "Not found")
    return obj


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/register")
def register(c: Creds, db=Depends(get_db)):
    email = c.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "That email is already registered. Try signing in.")
    u = User(email=email, password_hash=hash_pw(c.password))
    db.add(u)
    db.commit()
    return {"token": make_token(u.id)}


@app.post("/api/login")
def login(c: Creds, db=Depends(get_db)):
    u = db.scalar(select(User).where(User.email == c.email.lower()))
    if not u or not check_pw(c.password, u.password_hash):
        raise HTTPException(401, "Wrong email or password.")
    return {"token": make_token(u.id)}


@app.post("/api/sessions")
def create_session(p: NewSession, db=Depends(get_db), user=Depends(current_user)):
    try:
        qs = llm.generate_questions(p.role, p.kind, p.difficulty, p.count)
    except Exception:
        raise HTTPException(502, "Could not generate questions. Please try again.")
    s = Interview(user_id=user.id, role=p.role.strip(), kind=p.kind, difficulty=p.difficulty,
                  questions=[Question(**q) for q in qs])
    db.add(s)
    db.commit()
    return s_out(s)


@app.get("/api/sessions")
def list_sessions(db=Depends(get_db), user=Depends(current_user)):
    rows = db.scalars(select(Interview).where(Interview.user_id == user.id)
                      .order_by(Interview.created_at.desc()).limit(50)).all()
    return [s_out(s, full=False) for s in rows]


@app.get("/api/sessions/{sid}")
def get_session(sid: int, db=Depends(get_db), user=Depends(current_user)):
    return s_out(own(db, Interview, sid, user))


@app.post("/api/questions/{qid}/answer")
def answer(qid: int, a: AnswerIn, db=Depends(get_db), user=Depends(current_user)):
    q = own(db, Question, qid, user)
    if q.answer:
        raise HTTPException(409, "This question is already answered.")
    s = db.get(Interview, q.interview_id)
    try:
        ev = llm.evaluate(s.role, s.kind, q.text, a.answer)
    except Exception:
        raise HTTPException(502, "Scoring failed. Please submit again.")
    q.answer, q.seconds = a.answer, a.seconds
    q.feedback, q.improved = ev["feedback"], ev["improved"]
    for k in DIMS:
        setattr(q, k, ev[k])
    db.flush()
    done = [x for x in s.questions if x.answer]
    s.overall = round(mean(mean(getattr(x, k) for k in DIMS) for x in done), 1)
    db.commit()
    return q_out(q)


@app.get("/api/analytics")
def analytics(db=Depends(get_db), user=Depends(current_user)):
    rows = db.scalars(select(Interview).where(Interview.user_id == user.id, Interview.overall.isnot(None))
                      .order_by(Interview.created_at)).all()
    qs = [q for r in rows for q in r.questions if q.answer]
    avg = {d: round(mean(getattr(q, d) for q in qs), 1) for d in DIMS} if qs else {}
    return {"answered": len(qs), "averages": avg, "weakest": min(avg, key=avg.get) if avg else None,
            "trend": [{"date": r.created_at.strftime("%b %d"), "score": r.overall} for r in rows][-20:]}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
