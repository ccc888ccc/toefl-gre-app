from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..models import VocabCard, VocabReview, ReviewEvent
from ..auth import current_user
from ..schemas import StatsOut, ForecastDay

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(current_user)])

MASTERED_INTERVAL = 21  # days; a card you won't see for 3+ weeks counts as "mastered"


@router.get("", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    today = date.today()

    total_cards = db.query(func.count(VocabCard.id)).scalar() or 0
    mastered = db.query(func.count(VocabReview.id)).filter(
        VocabReview.interval_days >= MASTERED_INTERVAL).scalar() or 0
    learning = db.query(func.count(VocabReview.id)).filter(
        VocabReview.total_seen > 0, VocabReview.interval_days < MASTERED_INTERVAL).scalar() or 0
    due_today = db.query(func.count(VocabReview.id)).filter(
        VocabReview.total_seen > 0, VocabReview.due_date <= today).scalar() or 0
    new_available = db.query(func.count(VocabReview.id)).filter(
        VocabReview.total_seen == 0).scalar() or 0

    # 7-day forecast of upcoming review load.
    forecast = []
    for i in range(7):
        d = today + timedelta(days=i)
        if i == 0:
            c = db.query(func.count(VocabReview.id)).filter(
                VocabReview.total_seen > 0, VocabReview.due_date <= d).scalar() or 0
        else:
            c = db.query(func.count(VocabReview.id)).filter(
                VocabReview.total_seen > 0, VocabReview.due_date == d).scalar() or 0
        forecast.append(ForecastDay(day=d, count=c))

    # Reviews done today + streak (consecutive days with >=1 review, counting back).
    reviewed_today = db.query(func.count(ReviewEvent.id)).filter(
        func.date(ReviewEvent.reviewed_at) == today.isoformat()).scalar() or 0

    active_days = {
        row[0] for row in db.query(func.date(ReviewEvent.reviewed_at)).distinct().all()
    }
    streak = 0
    cursor = today
    while cursor.isoformat() in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    return StatsOut(
        total_cards=total_cards, mastered=mastered, learning=learning,
        due_today=due_today, new_available=new_available,
        streak_days=streak, reviewed_today=reviewed_today, forecast=forecast,
    )
