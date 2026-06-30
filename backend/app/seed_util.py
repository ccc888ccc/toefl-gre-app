"""Helpers to (a) ensure the admin login account exists and (b) import vocab
cards from a CSV into the SHARED deck. Used at startup and by the seed scripts."""
import csv

from sqlalchemy.orm import Session

from .config import settings
from .models import User, VocabCard
from .auth import hash_password

CSV_FIELDS = ["word", "part_of_speech", "definition_en", "definition_zh",
              "example", "synonyms", "tags"]


def ensure_user(db: Session) -> None:
    """Ensure the .env account exists and is the admin. The admin can use every
    tool (vocab, grader, reading/listening review) and manage member accounts."""
    user = db.query(User).filter(User.username == settings.app_username).first()
    if user is None:
        db.add(User(username=settings.app_username,
                    password_hash=hash_password(settings.app_password),
                    role="admin"))
        db.commit()
    elif user.role != "admin":
        user.role = "admin"
        db.commit()


def import_cards_from_csv(db: Session, csv_path: str) -> int:
    """Insert cards from CSV into the shared deck, skipping words already present
    (case-insensitive). Returns the count added. No VocabReview rows are created
    here: each user's SRS progress starts lazily the first time THEY study a card."""
    existing = {w.lower() for (w,) in db.query(VocabCard.word).all()}
    added = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            word = (row.get("word") or "").strip()
            if not word or word.lower() in existing:
                continue
            card = VocabCard(**{k: (row.get(k) or "").strip() or None for k in CSV_FIELDS})
            card.word = word
            db.add(card)
            existing.add(word.lower())
            added += 1
    db.commit()
    return added
