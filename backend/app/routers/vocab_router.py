from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..config import settings
from ..models import VocabCard, VocabReview, ReviewEvent
from ..auth import current_user
from ..srs import update_sm2
from ..schemas import (
    CardCreate, CardOut, ReviewCardOut, ReviewIn, ReviewOut, DueQueueOut,
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


@router.get("/queue", response_model=DueQueueOut)
def queue(new_limit: int | None = None, db: Session = Depends(get_db)):
    """Today's study queue: all due review cards + up to `new_limit` fresh cards."""
    today = date.today()
    if new_limit is None:
        new_limit = settings.daily_new_cards

    q = db.query(VocabCard).options(joinedload(VocabCard.review)).join(VocabReview)

    due = (q.filter(VocabReview.total_seen > 0, VocabReview.due_date <= today)
             .order_by(VocabReview.due_date).all())
    new = (q.filter(VocabReview.total_seen == 0)
             .order_by(VocabCard.id).limit(max(0, new_limit)).all())

    cards = [_review_card_out(c) for c in due] + [_review_card_out(c) for c in new]
    return DueQueueOut(due_count=len(due), new_count=len(new), cards=cards)


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


@router.post("/cards", response_model=CardOut, status_code=status.HTTP_201_CREATED)
def add_card(body: CardCreate, db: Session = Depends(get_db)):
    """Quick add a new word (from 學而思 / 做題時遇到的生字). Becomes a new card due today."""
    card = VocabCard(**body.model_dump())
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
    return query.order_by(VocabCard.word).offset(offset).limit(min(limit, 500)).all()
