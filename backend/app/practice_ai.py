"""Tool 3: explain a missed reading/listening question with Claude.
Reuses the grader's Claude caller. Returns a 4-field JSON, all in 繁體中文."""
import json

from . import grader
from .grader import GraderError

PROMPT = """You are an expert TOEFL {section} tutor. A student answered a practice \
question incorrectly and wants to understand it. Explain clearly and concisely.

QUESTION TYPE: {qtype}
QUESTION:
\"\"\"{question}\"\"\"
STUDENT'S CHOICE: {user_choice}
CORRECT ANSWER: {correct_choice}

Return ONLY a JSON object (no markdown, no commentary) with EXACTLY these keys, \
ALL written in Traditional Chinese (繁體中文):
{{
  "summary_zh": "<2-3 句重點總結>",
  "why_correct_zh": "<為什麼正確答案是對的>",
  "why_wrong_zh": "<為什麼學生的選項是錯的 / 掉進什麼陷阱>",
  "type_strategy_zh": "<這個題型的通用解法、陷阱與技巧>"
}}
Output only the JSON object."""


def explain(section: str, question_text: str | None, question_type: str | None,
            user_choice: str | None, correct_choice: str | None) -> dict:
    prompt = PROMPT.format(
        section=section or "reading",
        qtype=question_type or "(未指定)",
        question=question_text or "(未提供題目)",
        user_choice=user_choice or "(未提供)",
        correct_choice=correct_choice or "(未提供)",
    )
    last_err = None
    for _ in range(2):
        raw = grader._call_claude(prompt)
        try:
            d = grader.parse_feedback(raw)
            return {
                "summary_zh": str(d.get("summary_zh", "")).strip(),
                "why_correct_zh": str(d.get("why_correct_zh", "")).strip(),
                "why_wrong_zh": str(d.get("why_wrong_zh", "")).strip(),
                "type_strategy_zh": str(d.get("type_strategy_zh", "")).strip(),
            }
        except (GraderError, json.JSONDecodeError) as e:
            last_err = e
    raise GraderError(f"無法解析解析結果: {last_err}")
