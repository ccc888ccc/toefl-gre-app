import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..config import settings
from ..models import VocabCard, VocabReview, ReviewEvent
from ..auth import current_user
from ..srs import update_sm2
from ..grader import GraderError
from ..vocab_ai import autofill_word
from ..schemas import (
    CardCreate, CardOut, ReviewCardOut, ReviewIn, ReviewOut,
    LearnIn, LearnQueueOut, ReviewQueueOut,
    AutofillIn, AutofillOut,
)

router = APIRouter(prefix="/api/vocab", tags=["vocab"], dependencies=[Depends(current_user)])


def _review_card_out(card: VocabCard) -> ReviewCardOut:
    r = card.review
    return ReviewCardOut(
        id=card.id, word=card.word, part_of_speech=card.part_of_speech,
        definition_en=card.definition_en, definition_zh=card.definition_zh,
        example=card.example, synonyms=card.synonyms, tags=card.tags,
        due_date=r.due_date if r else None,
        repetitions=r.repetitions if r else 0,
        is_new=bool(r and r.total_seen == 0),
    )


def _find_existing(db: Session, word: str) -> VocabCard | None:
    """Case-insensitive lookup so 'Ubiquitous' and 'ubiquitous' count as the same."""
    return db.query(VocabCard).filter(func.lower(VocabCard.word) == word.lower()).first()


@router.get("/learn", response_model=LearnQueueOut)
def learn_queue(db: Session = Depends(get_db)):
    """First-time learning zone: words never seen yet, in the order they were
    added (no daily cap). The user just reads each card; no flip, no self-grade.
    Marking one learned (POST /learn) moves it into the review zone."""
    q = db.query(VocabCard).options(joinedload(VocabCard.review)).join(VocabReview)
    new = (q.filter(VocabReview.total_seen == 0)
             .order_by(VocabCard.id).all())
    return LearnQueueOut(new_count=len(new), cards=[_review_card_out(c) for c in new])


@router.post("/learn", response_model=ReviewOut)
def mark_learned(body: LearnIn, db: Session = Depends(get_db)):
    """Mark a brand-new word as learned. It leaves the learning zone and enters
    the review zone, scheduled like a first successful pass (due tomorrow)."""
    card = db.get(VocabCard, body.card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    r = card.review
    if r is None:
        r = VocabReview(card_id=card.id)
        db.add(r)
    r.repetitions = 1
    r.interval_days = 1
    r.due_date = date.today() + timedelta(days=1)
    r.last_reviewed = datetime.utcnow()
    r.total_seen = max(r.total_seen, 1)
    db.commit()
    db.refresh(r)
    return ReviewOut(
        card_id=card.id, ease_factor=r.ease_factor, interval_days=r.interval_days,
        repetitions=r.repetitions, due_date=r.due_date, correct=True,
    )


@router.get("/review", response_model=ReviewQueueOut)
def review_queue(db: Session = Depends(get_db)):
    """Review zone: only words already learned AND due today (SM-2 schedule).
    The due batch is shuffled so the order is different every session."""
    today = date.today()
    q = db.query(VocabCard).options(joinedload(VocabCard.review)).join(VocabReview)
    due = q.filter(VocabReview.total_seen > 0, VocabReview.due_date <= today).all()
    random.shuffle(due)
    return ReviewQueueOut(due_count=len(due), cards=[_review_card_out(c) for c in due])


@router.post("/review", response_model=ReviewOut)
def review(body: ReviewIn, db: Session = Depends(get_db)):
    card = db.get(VocabCard, body.card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    r = card.review
    if r is None:
        r = VocabReview(card_id=card.id)
        db.add(r)
    res = update_sm2(r.ease_factor, r.interval_days, r.repetitions, body.grade)
    r.ease_factor = res.ease_factor
    r.interval_days = res.interval_days
    r.repetitions = res.repetitions
    r.due_date = date.today() + timedelta(days=res.interval_days)
    r.last_reviewed = datetime.utcnow()
    r.total_seen += 1
    if res.correct:
        r.total_correct += 1
    db.add(ReviewEvent(card_id=card.id, grade=body.grade))
    db.commit()
    db.refresh(r)
    return ReviewOut(
        card_id=card.id, ease_factor=r.ease_factor, interval_days=r.interval_days,
        repetitions=r.repetitions, due_date=r.due_date, correct=res.correct,
    )


@router.get("/check", response_model=dict)
def check(word: str, db: Session = Depends(get_db)):
    """Quick existence check so the UI can warn before adding a duplicate."""
    return {"exists": _find_existing(db, word.strip()) is not None}


@router.post("/autofill", response_model=AutofillOut)
def autofill(body: AutofillIn):
    if not body.word.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "word required")
    try:
        return autofill_word(body.word.strip())
    except GraderError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))


@router.post("/cards", response_model=CardOut, status_code=status.HTTP_201_CREATED)
def add_card(body: CardCreate, db: Session = Depends(get_db)):
    """Quick add a new word. Rejects case-insensitive duplicates so your own
    word-book additions never create a second copy of a word already in the deck."""
    word = (body.word or "").strip()
    if not word:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "word required")
    if _find_existing(db, word):
        raise HTTPException(status.HTTP_409_CONFLICT, f"「{word}」已在字庫中，沒有重複加入。")
    data = body.model_dump()
    data["word"] = word
    card = VocabCard(**data)
    db.add(card)
    db.flush()
    db.add(VocabReview(card_id=card.id, due_date=date.today()))
    db.commit()
    db.refresh(card)
    return card


@router.get("/cards", response_model=list[CardOut])
def list_cards(limit: int = 100, offset: int = 0, q: str | None = None,
               db: Session = Depends(get_db)):
    query = db.query(VocabCard)
    if q:
        query = query.filter(VocabCard.word.ilike(f"%{q}%"))
    return query.order_by(VocabCard.word).offset(offset).limit(min(limit, 3000)).all()
