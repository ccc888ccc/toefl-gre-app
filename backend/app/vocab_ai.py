"""Fill in one vocab card (pos / EN def / ZH def / example / synonyms) from just
the word, using Claude. Reuses the grader's Claude caller so the API key handling
lives in one place. Used by POST /api/vocab/autofill."""
import json

from . import grader
from .grader import GraderError

AUTOFILL_PROMPT = """You are building ONE GRE/TOEFL vocabulary flashcard for a learner \
whose native language is Traditional Chinese.

For the word "{word}", return ONLY a JSON object with EXACTLY these keys:
- "part_of_speech": short form, e.g. "adj", "n", "v", "adv"
- "definition_en": a concise English definition (one clause)
- "definition_zh": the meaning in Traditional Chinese (繁體中文)
- "example": one natural example sentence using the word
- "synonyms": 2-4 synonyms separated by "; "

Output only the JSON object. No markdown, no code fences, no commentary."""


def autofill_word(word: str) -> dict:
    prompt = AUTOFILL_PROMPT.format(word=word)
    last_err = None
    for _ in range(2):  # one retry on parse failure
        raw = grader._call_claude(prompt)
        try:
            data = grader.parse_feedback(raw)
            return {
                "part_of_speech": str(data.get("part_of_speech", "")).strip(),
                "definition_en": str(data.get("definition_en", "")).strip(),
                "definition_zh": str(data.get("definition_zh", "")).strip(),
                "example": str(data.get("example", "")).strip(),
                "synonyms": str(data.get("synonyms", "")).strip(),
            }
        except (GraderError, json.JSONDecodeError) as e:
            last_err = e
    raise GraderError(f"無法產生卡片內容: {last_err}")
