import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PracticeLog
from ..auth import current_user
from ..grader import GraderError
from ..practice_ai import explain
from ..schemas import PracticeSubmitIn, PracticeLogOut, PracticeExplanation, TypeStat

router = APIRouter(prefix="/api/practice", tags=["practice"],
                   dependencies=[Depends(current_user)])


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _to_out(log: PracticeLog) -> PracticeLogOut:
    expl = (PracticeExplanation(**json.loads(log.ai_explanation))
            if log.ai_explanation else PracticeExplanation())
    return PracticeLogOut(
        id=log.id, section=log.section, source=log.source,
        question_text=log.question_text, question_type=log.question_type,
        user_choice=log.user_choice, correct_choice=log.correct_choice,
        is_correct=log.is_correct, explanation=expl, created_at=log.created_at,
    )


@router.post("/submit", response_model=PracticeLogOut)
def submit(body: PracticeSubmitIn, db: Session = Depends(get_db)):
    if body.section not in ("reading", "listening"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "section must be reading or listening")
    is_correct = None
    if body.user_choice and body.correct_choice:
        is_correct = _norm(body.user_choice) == _norm(body.correct_choice)
    try:
        expl = explain(body.section, body.question_text, body.question_type,
                       body.user_choice, body.correct_choice)
    except GraderError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))

    log = PracticeLog(
        section=body.section, source=body.source, question_text=body.question_text,
        question_type=body.question_type, user_choice=body.user_choice,
        correct_choice=body.correct_choice, is_correct=is_correct,
        ai_explanation=json.dumps(expl, ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return _to_out(log)


@router.get("/logs", response_model=list[PracticeLogOut])
def logs(limit: int = 50, section: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PracticeLog)
    if section:
        q = q.filter(PracticeLog.section == section)
    rows = q.order_by(PracticeLog.created_at.desc()).limit(min(limit, 300)).all()
    return [_to_out(r) for r in rows]


@router.get("/type-stats", response_model=list[TypeStat])
def type_stats(db: Session = Depends(get_db)):
    rows = db.query(PracticeLog).filter(PracticeLog.question_type.isnot(None)).all()
    agg: dict[str, dict] = {}
    for r in rows:
        a = agg.setdefault(r.question_type, {"total": 0, "correct": 0})
        a["total"] += 1
        if r.is_correct:
            a["correct"] += 1
    out = [TypeStat(question_type=k, total=v["total"], correct=v["correct"],
                    accuracy=round(v["correct"] / v["total"], 3) if v["total"] else 0.0)
           for k, v in agg.items()]
    out.sort(key=lambda t: t.accuracy)  # weakest types first
    return out
