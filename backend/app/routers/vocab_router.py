import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, aliased

from ..database import get_db
from ..models import VocabCard, VocabReview, ReviewEvent, User
from ..auth import current_user, current_user_obj
from ..srs import update_sm2
from ..grader import GraderError
from ..vocab_ai import autofill_word
from ..schemas import (
    CardCreate, CardOut, ReviewCardOut, ReviewIn, ReviewOut,
    LearnIn, LearnQueueOut, ReviewQueueOut,
    AutofillIn, AutofillOut,
)

# The vocab deck is SHARED across all users; SRS progress (VocabReview) is
# per-user, created lazily the first time a user learns/reviews a card.
router = APIRouter(prefix="/api/vocab", tags=["vocab"], dependencies=[Depends(current_user)])


def _review_card_out(card: VocabCard, review: VocabReview | None) -> ReviewCardOut:
    return ReviewCardOut(
        id=card.id, word=card.word, part_of_speech=card.part_of_speech,
        definition_en=card.definition_en, definition_zh=card.definition_zh,
        example=card.example, synonyms=card.synonyms, tags=card.tags,
        due_date=review.due_date if review else None,
        repetitions=review.repetitions if review else 0,
        is_new=(review is None or review.total_seen == 0),
    )


def _find_existing(db: Session, word: str) -> VocabCard | None:
    """Case-insensitive lookup so 'Ubiquitous' and 'ubiquitous' count as the same."""
    return db.query(VocabCard).filter(func.lower(VocabCard.word) == word.lower()).first()


def _get_or_create_review(db: Session, user_id: int, card_id: int) -> VocabReview:
    """Fetch this user's SRS row for a card, creating a fresh one (with SM-2
    defaults) if they have never studied it before."""
    r = (db.query(VocabReview)
           .filter(VocabReview.user_id == user_id, VocabReview.card_id == card_id)
           .first())
    if r is None:
        r = VocabReview(
            user_id=user_id, card_id=card_id, ease_factor=2.5, interval_days=0,
            repetitions=0, due_date=date.today(), total_seen=0, total_correct=0,
        )
        db.add(r)
    return r


@router.get("/learn", response_model=LearnQueueOut)
def learn_queue(db: Session = Depends(get_db), user: User = Depends(current_user_obj)):
    """First-time learning zone for THIS user: words they have never studied
    (no review row yet, or one with total_seen == 0), in the order added."""
    rev = aliased(VocabReview)
    rows = (db.query(VocabCard, rev)
              .outerjoin(rev, and_(rev.card_id == VocabCard.id, rev.user_id == user.id))
              .filter(or_(rev.id.is_(None), rev.total_seen == 0))
              .order_by(VocabCard.id).all())
    return LearnQueueOut(new_count=len(rows), cards=[_review_card_out(c, r) for c, r in rows])


@router.post("/learn", response_model=ReviewOut)
def mark_learned(body: LearnIn, db: Session = Depends(get_db),
                 user: User = Depends(current_user_obj)):
    """Mark a brand-new word as learned for this user; it enters their review
    zone, scheduled like a first successful pass (due tomorrow)."""
    card = db.get(VocabCard, body.card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    r = _get_or_create_review(db, user.id, card.id)
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
def review_queue(db: Session = Depends(get_db), user: User = Depends(current_user_obj)):
    """Review zone for THIS user: words they have learned AND that are due today
    (SM-2 schedule), shuffled so the order differs every session."""
    today = date.today()
    rows = (db.query(VocabCard, VocabReview)
              .join(VocabReview, VocabReview.card_id == VocabCard.id)
              .filter(VocabReview.user_id == user.id,
                      VocabReview.total_seen > 0,
                      VocabReview.due_date <= today).all())
    random.shuffle(rows)
    return ReviewQueueOut(due_count=len(rows), cards=[_review_card_out(c, r) for c, r in rows])


@router.post("/review", response_model=ReviewOut)
def review(body: ReviewIn, db: Session = Depends(get_db),
           user: User = Depends(current_user_obj)):
    card = db.get(VocabCard, body.card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")
    r = _get_or_create_review(db, user.id, card.id)
    res = update_sm2(r.ease_factor, r.interval_days, r.repetitions, body.grade)
    r.ease_factor = res.ease_factor
    r.interval_days = res.interval_days
    r.repetitions = res.repetitions
    r.due_date = date.today() + timedelta(days=res.interval_days)
    r.last_reviewed = datetime.utcnow()
    r.total_seen += 1
    if res.correct:
        r.total_correct += 1
    db.add(ReviewEvent(user_id=user.id, card_id=card.id, grade=body.grade))
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
    """Add a new word to the SHARED deck. Any user (admin or member) may add.
    Rejects case-insensitive duplicates. No review row is created here -- each
    user's SRS progress starts the first time THEY learn the word, so a newly
    added word shows up as 'new' for everyone (including the person who added it)."""
    word = (body.word or "").strip()
    if not word:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "word required")
    if _find_existing(db, word):
        raise HTTPException(status.HTTP_409_CONFLICT, f"「{word}」已在字庫中，沒有重複加入。")
    data = body.model_dump()
    data["word"] = word
    card = VocabCard(**data)
    db.add(card)
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
