"""Generate a GRE high-frequency vocab deck with Claude and import it into the DB.

Runs on YOUR machine with YOUR ANTHROPIC_API_KEY (read from backend/.env), so the
key never leaves the backend. Words already in the DB are excluded so you can run it
repeatedly / resume. De-dup is case-insensitive.

Usage (run via fill_vocab.bat, or from the backend folder):
    python ../seed/generate_vocab.py --target 1000 --batch 25
"""
import argparse
import json
import os
import random
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.config import settings                      # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import VocabCard, VocabReview        # noqa: E402

import anthropic                                      # noqa: E402

PROMPT_TEMPLATE = """You are building a GRE high-frequency vocabulary deck for an advanced learner \
whose native language is Traditional Chinese.

Give me {n} GRE words that are genuinely useful for the GRE Verbal section and that are NOT \
in this ALREADY-HAVE list:
{exclude}

IMPORTANT for variety (the deck already has {have} words, so common picks are likely taken):
- Spread your choices across MANY different initial letters (not just a, b, c).
- Avoid the most obvious textbook examples; include solid but less-cliché GRE words too.
- Absolutely do not repeat any word from the ALREADY-HAVE list above.

For each word return an object with EXACTLY these keys:
- "word": the word, lowercase
- "part_of_speech": short form, e.g. "adj", "n", "v", "adv"
- "definition_en": a concise English definition (one clause)
- "definition_zh": the meaning in Traditional Chinese (繁體中文)
- "example": one natural example sentence using the word
- "synonyms": 2-4 synonyms separated by "; "

Output ONLY a JSON array of objects. No prose, no markdown fences."""

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_json_array(text: str):
    text = FENCE_RE.sub("", text.strip())
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--tag", default="high-frequency")
    ap.add_argument("--max-stall", type=int, default=4,
                    help="stop after this many batches that add (almost) nothing")
    args = ap.parse_args()

    if not settings.anthropic_api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set in backend/.env")

    Base.metadata.create_all(bind=engine)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    db = SessionLocal()

    try:
        existing = {w.lower() for (w,) in db.query(VocabCard.word).all()}
        print(f"Starting with {len(existing)} cards; target {args.target}.")
        stall = 0

        while len(existing) < args.target:
            need = min(args.batch, args.target - len(existing))
            # Representative RANDOM sample across the WHOLE deck (not the alphabetical
            # tail) so the model actually sees what's already taken and stops repeating.
            pool = list(existing)
            random.shuffle(pool)
            exclude = ", ".join(sorted(pool[:700])) if pool else "(none yet)"
            prompt = PROMPT_TEMPLATE.format(n=need, exclude=exclude, have=len(existing))

            msg = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )
            try:
                cards = parse_json_array(msg.content[0].text)
            except (json.JSONDecodeError, IndexError) as e:
                print(f"  ! parse failed ({e}); retrying")
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

            # Stop early if the model keeps repeating words it already gave us.
            if added <= max(1, need // 10):
                stall += 1
                if stall >= args.max_stall:
                    print(f"\nStopping: the model is mostly repeating existing words "
                          f"(net gain tiny for {stall} batches in a row).")
                    print(f"You have {len(existing)} unique words. Re-run later to try for more, "
                          f"or lower your sights — a clean high-frequency set naturally caps out.")
                    break
            else:
                stall = 0

        print(f"Done. {len(existing)} cards in DB.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
