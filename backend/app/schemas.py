"""Pydantic request/response models."""
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CardBase(BaseModel):
    word: str
    part_of_speech: str | None = None
    definition_en: str | None = None
    definition_zh: str | None = None
    example: str | None = None
    synonyms: str | None = None
    tags: str | None = None


class CardCreate(CardBase):
    pass


class CardOut(CardBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ReviewCardOut(CardOut):
    """A card plus its current SRS state, as served to the review screen."""
    due_date: date | None = None
    repetitions: int = 0
    is_new: bool = True


class ReviewIn(BaseModel):
    card_id: int
    grade: str  # again | hard | good | easy


class ReviewOut(BaseModel):
    card_id: int
    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: date
    correct: bool


class DueQueueOut(BaseModel):
    due_count: int
    new_count: int
    cards: list[ReviewCardOut]


class ForecastDay(BaseModel):
    day: date
    count: int


class StatsOut(BaseModel):
    total_cards: int
    mastered: int           # cards with interval >= 21 days
    learning: int
    due_today: int
    new_available: int
    streak_days: int
    reviewed_today: int
    forecast: list[ForecastDay]
