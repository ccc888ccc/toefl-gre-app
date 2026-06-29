"""Helpers to (a) ensure the single login account exists and (b) import vocab
cards from a CSV into the DB. Used at startup and by the seed scripts."""
import csv
from datetime import date

from sqlalchemy.orm import Session

from .config import settings
from .models import User, VocabCard, VocabReview
from .auth import hash_password

CSV_FIELDS = ["word", "part_of_speech", "definition_en", "definition_zh",
              "example", "synonyms", "tags"]


def ensure_user(db: Session) -> None:
    user = db.query(User).filter(User.username == settings.app_username).first()
    if user is None:
        db.add(User(username=settings.app_username,
                    password_hash=hash_password(settings.app_password)))
        db.commit()


def import_cards_from_csv(db: Session, csv_path: str) -> int:
    """Insert cards from CSV, skipping words already present. Returns count added."""
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
            db.flush()
            db.add(VocabReview(card_id=card.id, due_date=date.today()))
            existing.add(word.lower())
            added += 1
    db.commit()
    return added
