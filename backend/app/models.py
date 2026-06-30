"""ORM models. Mirrors the schema in the spec (section 2).

The vocab deck (vocab_cards) is SHARED across users; SRS progress (vocab_reviews)
and the grade log (review_events) are PER-USER. Users have a role (admin/member)
that gates the writing/practice tools.
"""
from datetime import datetime, date
from sqlalchemy import (
    Integer, String, Text, Float, Date, DateTime, ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="member")  # 'admin' | 'member'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VocabCard(Base):
    __tablename__ = "vocab_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(128), index=True)
    part_of_speech: Mapped[str | None] = mapped_column(String(64), nullable=True)
    definition_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    synonyms: Mapped[str | None] = mapped_column(Text, nullable=True)   # GRE focus
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # The deck is SHARED. Per-user SRS progress lives in VocabReview, keyed by
    # (user_id, card_id) -- a card has many review rows, one per learner, created
    # lazily the first time a user studies it.


class VocabReview(Base):
    """Per-USER, per-card SRS state (SM-2). One row per (user_id, card_id)."""
    __tablename__ = "vocab_reviews"
    __table_args__ = (UniqueConstraint("user_id", "card_id", name="uq_vocab_reviews_user_card"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("vocab_cards.id"), index=True)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    due_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_seen: Mapped[int] = mapped_column(Integer, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, default=0)


class ReviewEvent(Base):
    """Append-only log of every grade, used for per-user streaks and daily-count
    stats. Also the natural sync target for the PWA offline queue later."""
    __tablename__ = "review_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("vocab_cards.id"), index=True)
    grade: Mapped[str] = mapped_column(String(8))   # again / hard / good / easy
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


# ============ Tool 2: writing / speaking grader (spec section 4) ============

class WritingSubmission(Base):
    __tablename__ = "writing_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_type: Mapped[str] = mapped_column(String(48), index=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_answer: Mapped[str] = mapped_column(Text)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("writing_submissions.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ErrorPattern(Base):
    """Running tally of the weakness categories Claude flags across submissions."""
    __tablename__ = "error_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============ Tool 3: reading / listening review (spec section 5) ============
from sqlalchemy import Boolean as _Boolean


class PracticeLog(Base):
    __tablename__ = "practice_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section: Mapped[str] = mapped_column(String(16), index=True)        # reading / listening
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)   # e.g. xueersi set 12
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    user_choice: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correct_choice: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(_Boolean, nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)   # Claude JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
