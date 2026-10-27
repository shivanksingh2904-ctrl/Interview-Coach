import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

url = os.getenv("DATABASE_URL", "sqlite:///./coach.db")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
engine = create_engine(url, pool_pre_ping=True,
                       connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))


class Interview(Base):
    __tablename__ = "interviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(default=now)
    overall: Mapped[float | None] = mapped_column(default=None)
    questions: Mapped[list["Question"]] = relationship(order_by="Question.id", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="general")
    answer: Mapped[str | None] = mapped_column(Text, default=None)
    seconds: Mapped[int] = mapped_column(default=0)
    clarity: Mapped[int | None] = mapped_column(default=None)
    structure: Mapped[int | None] = mapped_column(default=None)
    relevance: Mapped[int | None] = mapped_column(default=None)
    depth: Mapped[int | None] = mapped_column(default=None)
    confidence: Mapped[int | None] = mapped_column(default=None)
    feedback: Mapped[str | None] = mapped_column(Text, default=None)
    improved: Mapped[str | None] = mapped_column(Text, default=None)
    interview: Mapped["Interview"] = relationship(viewonly=True)
