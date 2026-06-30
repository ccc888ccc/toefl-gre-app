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
    due_date: date | None = None
    repetitions: int = 0
    is_new: bool = True


class ReviewIn(BaseModel):
    card_id: int
    grade: str  # again | hard | good | easy


class LearnIn(BaseModel):
    card_id: int


class ReviewOut(BaseModel):
    card_id: int
    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: date
    correct: bool


class LearnQueueOut(BaseModel):
    new_count: int
    cards: list[ReviewCardOut]


class ReviewQueueOut(BaseModel):
    due_count: int
    cards: list[ReviewCardOut]


class ForecastDay(BaseModel):
    day: date
    count: int


class StatsOut(BaseModel):
    total_cards: int
    mastered: int
    learning: int
    due_today: int
    new_available: int
    streak_days: int
    reviewed_today: int
    forecast: list[ForecastDay]


# ---------- Tool 2: writing / speaking grader ----------

class WritingSubmitIn(BaseModel):
    task_type: str
    prompt: str | None = None
    user_answer: str
    parent_id: int | None = None


class ProblemSentence(BaseModel):
    original: str = ""
    issue: str = ""
    rewrite: str = ""


class Feedback(BaseModel):
    score_overall: float | None = None
    breakdown: dict[str, float] = {}
    problem_sentences: list[ProblemSentence] = []
    weaknesses: list[str] = []
    model_high_score_version: str = ""
    summary_zh: str = ""


class WritingSubmissionOut(BaseModel):
    id: int
    task_type: str
    prompt: str | None = None
    user_answer: str
    feedback: Feedback
    parent_id: int | None = None
    parent_score: float | None = None
    created_at: datetime


class SubmissionListItem(BaseModel):
    id: int
    task_type: str
    score_overall: float | None = None
    prompt_preview: str = ""
    parent_id: int | None = None
    created_at: datetime


class WeaknessItem(BaseModel):
    category: str
    count: int
    last_seen: datetime


class PromptSample(BaseModel):
    task_type: str
    prompt: str


class AutofillIn(BaseModel):
    word: str


class AutofillOut(BaseModel):
    part_of_speech: str = ""
    definition_en: str = ""
    definition_zh: str = ""
    example: str = ""
    synonyms: str = ""


# ---------- Tool 3: reading / listening review ----------

class PracticeSubmitIn(BaseModel):
    section: str                       # reading / listening
    source: str | None = None
    question_text: str | None = None
    question_type: str | None = None
    user_choice: str | None = None
    correct_choice: str | None = None


class PracticeExplanation(BaseModel):
    summary_zh: str = ""
    why_correct_zh: str = ""
    why_wrong_zh: str = ""
    type_strategy_zh: str = ""


class PracticeLogOut(BaseModel):
    id: int
    section: str
    source: str | None = None
    question_text: str | None = None
    question_type: str | None = None
    user_choice: str | None = None
    correct_choice: str | None = None
    is_correct: bool | None = None
    explanation: PracticeExplanation
    created_at: datetime


class TypeStat(BaseModel):
    question_type: str
    total: int
    correct: int
    accuracy: float
