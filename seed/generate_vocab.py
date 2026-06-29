"""Generate a GRE high-frequency vocab deck with Claude and import it into the DB.

Runs on YOUR machine with YOUR ANTHROPIC_API_KEY (read from backend/.env), so the
key never leaves the backend. Claude picks high-frequency GRE words and writes the
full card (definition EN/ZH, example, synonyms) for each. Words already in the DB
are excluded so you can run it repeatedly / resume.

Usage (from the repo root, with backend deps installed):
    python seed/generate_vocab.py --target 1000 --batch 25

Cost note: ~1000 cards is many small completions. It's cheap on Sonnet but not free;
the script prints progress and you can Ctrl-C and resume anytime (already-saved
words persist).
"""
import argparse
import json
import os
import re
import sys
from datetime import date

# Make the backend package importable.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.config import settings                      # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import VocabCard, VocabReview        # noqa: E402

import anthropic                                      # noqa: E402

PROMPT_TEMPLATE = """You are building a GRE high-frequency vocabulary deck for an advanced learner \
whose native language is Traditional Chinese.

Give me {n} GRE high-frequency words that are NOT in this exclude list:
{exclude}

For each word return an object with EXACTLY these keys:
- "word": the word, lowercase
- "part_of_speech": short form, e.g. "adj", "n", "v", "adv"
- "definition_en": a concise English definition (one clause)
- "definition_zh": the meaning in Traditional Chinese (繁體中文)
- "example": one natural example sentence using the word
- "synonyms": 2-4 synonyms separated by "; " (important for GRE)

Rules:
- Choose genuinely high-frequency GRE words (the kind on Magoosh/Manhattan frequency lists), \
not obscure trivia and not easy everyday words.
- Output ONLY a JSON array of objects. No prose, no markdown fences, no trailing commentary.
"""

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_json_array(text: str):
    text = FENCE_RE.sub("", text.strip())
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000, help="total cards wanted in DB")
    ap.add_argument("--batch", type=int, default=25, help="words per Claude call")
    ap.add_argument("--tag", default="high-frequency")
    args = ap.parse_args()

    if not settings.anthropic_api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set in backend/.env")

    Base.metadata.create_all(bind=engine)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    db = SessionLocal()

    try:
        existing = {w.lower() for (w,) in db.query(VocabCard.word).all()}
        print(f"Starting with {len(existing)} cards; target {args.target}.")

        while len(existing) < args.target:
            need = min(args.batch, args.target - len(existing))
            # Cap the exclude list sent to the model to keep prompts small; local
            # dedup below is the real guard against repeats.
            exclude_sample = sorted(existing)[-400:]
            prompt = PROMPT_TEMPLATE.format(
                n=need, exclude=", ".join(exclude_sample) if exclude_sample else "(none yet)")

            msg = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )
            try:
                cards = parse_json_array(msg.content[0].text)
            except (json.JSONDecodeError, IndexError) as e:
                print(f"  ! parse failed ({e}); retrying batch")
                continue

            added = 0
            for c in cards:
                word = (c.get("word") or "").strip().lower()
                if not word or word in existing:
                    continue
                card = VocabCard(
                    word=word,
                    part_of_speech=(c.get("part_of_speech") or "").strip() or None,
                    definition_en=(c.get("definition_en") or "").strip() or None,
                    definition_zh=(c.get("definition_zh") or "").strip() or None,
                    example=(c.get("example") or "").strip() or None,
                    synonyms=(c.get("synonyms") or "").strip() or None,
                    tags=args.tag,
                )
                db.add(card)
                db.flush()
                db.add(VocabReview(card_id=card.id, due_date=date.today()))
                existing.add(word)
                added += 1
            db.commit()
            print(f"  +{added} (total {len(existing)})")

        print(f"Done. {len(existing)} cards in DB.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
