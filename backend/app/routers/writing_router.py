import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import WritingSubmission, ErrorPattern
from ..auth import require_admin
from ..grader import grade, GraderError, TASK_SPECS
from ..schemas import (
    WritingSubmitIn, WritingSubmissionOut, Feedback, SubmissionListItem,
    WeaknessItem, PromptSample,
)

# Admin-only: the writing / speaking grader is not available to member accounts.
router = APIRouter(prefix="/api/writing", tags=["writing"],
                   dependencies=[Depends(require_admin)])

# Built-in 2026-format prompts so you can practice without hunting for a question.
PROMPT_BANK: list[dict] = [
    {"task_type": "toefl_writing_email",
     "prompt": "You recently bought a laptop online, but it arrived with a cracked screen. "
               "Write an email to the online store's customer-service team. Explain the problem, "
               "say how it has affected you, and request a specific solution."},
    {"task_type": "toefl_writing_email",
     "prompt": "Your professor announced that next week's class will be moved online. Write an email "
               "to your professor asking two questions about the change and explaining one concern "
               "you have about attending online."},
    {"task_type": "toefl_writing_academic_discussion",
     "prompt": "Your professor is teaching a class on economics. Doctor Achebe asks: 'Some people "
               "think governments should prioritize economic growth above environmental protection. "
               "Others disagree. What is your view, and why?' Write a post contributing your opinion."},
    {"task_type": "toefl_writing_academic_discussion",
     "prompt": "Doctor Lee asks: 'Should universities require all students to take public-speaking "
               "courses? Why or why not?' Write a post contributing your opinion with reasons."},
    {"task_type": "toefl_speaking_listen_repeat",
     "prompt": "The committee has decided to postpone the annual conference until early next spring."},
    {"task_type": "toefl_speaking_interview",
     "prompt": "Interviewer: 'Tell me about a skill you would like to learn in the future and explain "
               "why it interests you.' (Paste your spoken-response transcript.)"},
    {"task_type": "gre_issue",
     "prompt": "\"Governments should focus on solving the immediate problems of today rather than on "
               "trying to solve the anticipated problems of the future.\" Write a response in which you "
               "discuss the extent to which you agree or disagree."},
    {"task_type": "gre_argument",
     "prompt": "The following appeared in a memo: 'Our sales fell last quarter after we reduced "
               "advertising. Therefore, to increase sales we should sharply increase our advertising "
               "budget.' Write a response discussing what questions must be answered to evaluate this argument."},
]


def _bump_error_patterns(db: Session, weaknesses: list[str]) -> None:
    now = datetime.utcnow()
    for cat in set(weaknesses):
        row = db.query(ErrorPattern).filter(ErrorPattern.category == cat).first()
        if row:
            row.count += 1
            row.last_seen = now
        else:
            db.add(ErrorPattern(category=cat, count=1, last_seen=now))


def _to_out(sub: WritingSubmission, db: Session) -> WritingSubmissionOut:
    fb = Feedback(**json.loads(sub.ai_feedback)) if sub.ai_feedback else Feedback()
    parent_score = None
    if sub.parent_id:
        parent = db.get(WritingSubmission, sub.parent_id)
        parent_score = parent.score_overall if parent else None
    return WritingSubmissionOut(
        id=sub.id, task_type=sub.task_type, prompt=sub.prompt,
        user_answer=sub.user_answer, feedback=fb, parent_id=sub.parent_id,
        parent_score=parent_score, created_at=sub.created_at,
    )


@router.get("/task-types")
def task_types():
    return [{"key": k, "label": v["label"], "dimensions": v["dimensions"], "scale": v["scale"]}
            for k, v in TASK_SPECS.items()]


@router.get("/prompts", response_model=list[PromptSample])
def prompts():
    return PROMPT_BANK


@router.post("/submit", response_model=WritingSubmissionOut)
def submit(body: WritingSubmitIn, db: Session = Depends(get_db)):
    if body.task_type not in TASK_SPECS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown task_type")
    if body.parent_id and not db.get(WritingSubmission, body.parent_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "parent submission not found")
    try:
        fb = grade(body.task_type, body.prompt, body.user_answer)
    except GraderError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))

    sub = WritingSubmission(
        task_type=body.task_type, prompt=body.prompt, user_answer=body.user_answer,
        ai_feedback=json.dumps(fb, ensure_ascii=False),
        score_overall=fb.get("score_overall"),
        score_breakdown=json.dumps(fb.get("breakdown", {}), ensure_ascii=False),
        parent_id=body.parent_id,
    )
    db.add(sub)
    _bump_error_patterns(db, fb.get("weaknesses", []))
    db.commit()
    db.refresh(sub)
    return _to_out(sub, db)


@router.get("/submissions", response_model=list[SubmissionListItem])
def submissions(limit: int = 50, db: Session = Depends(get_db)):
    rows = (db.query(WritingSubmission)
              .order_by(WritingSubmission.created_at.desc())
              .limit(min(limit, 200)).all())
    return [SubmissionListItem(
        id=r.id, task_type=r.task_type, score_overall=r.score_overall,
        prompt_preview=((r.prompt or "")[:80]), parent_id=r.parent_id,
        created_at=r.created_at,
    ) for r in rows]


@router.get("/submissions/{sub_id}", response_model=WritingSubmissionOut)
def submission(sub_id: int, db: Session = Depends(get_db)):
    sub = db.get(WritingSubmission, sub_id)
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    return _to_out(sub, db)


@router.get("/weaknesses", response_model=list[WeaknessItem])
def weaknesses(limit: int = 12, db: Session = Depends(get_db)):
    rows = (db.query(ErrorPattern)
              .order_by(ErrorPattern.count.desc())
              .limit(min(limit, 50)).all())
    return [WeaknessItem(category=r.category, count=r.count, last_seen=r.last_seen)
            for r in rows]
