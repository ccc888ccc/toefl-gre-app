"""Tool 2: writing / speaking grader (spec section 4, updated for the 2026 TOEFL).

2026 TOEFL iBT task types supported here:
  - Write an Email
  - Write for an Academic Discussion
  - Speaking: Listen and Repeat
  - Speaking: Take an Interview
Plus GRE Analytical Writing (Issue / Argument), which is unchanged.

Builds a per-task-type prompt, asks Claude to grade against the rubric and return
STRICT JSON only, then parses it robustly. The Claude API key lives in backend/.env
and is used only here on the server.
"""
import json
import re

from .config import settings

# Each task type: human label + rubric dimensions (snake_case keys used in the
# returned "breakdown") + the score scale. TOEFL 2026 uses a 1-6 band scale.
TASK_SPECS: dict[str, dict] = {
    "toefl_writing_email": {
        "label": "TOEFL Writing – Write an Email",
        "dimensions": ["development", "organization", "language_use"],
        "scale": "1-6",
        "guidance": "This is the 2026 TOEFL 'Write an Email' task. Judge task fulfillment "
                    "(does it address the situation and cover all required points), an "
                    "appropriate and consistent email register/tone, clear organization, "
                    "and accurate, varied language.",
    },
    "toefl_writing_academic_discussion": {
        "label": "TOEFL Writing – Academic Discussion",
        "dimensions": ["development", "organization", "language_use"],
        "scale": "1-6",
        "guidance": "This is the 2026 TOEFL 'Write for an Academic Discussion' task "
                    "(about 200-250 words). Judge how well the response contributes a clear, "
                    "well-supported opinion to the online discussion, with relevant elaboration "
                    "and effective, varied language.",
    },
    "toefl_speaking_listen_repeat": {
        "label": "TOEFL Speaking – Listen and Repeat",
        "dimensions": ["accuracy", "delivery", "language_use"],
        "scale": "1-6",
        "guidance": "This is the 2026 TOEFL 'Listen and Repeat' speaking task. The PROMPT is the "
                    "target sentence the test-taker had to repeat; the RESPONSE is a transcript of "
                    "what they actually said. Judge accuracy (how completely and correctly the "
                    "sentence was reproduced — missing/changed words lower this), delivery (fluency "
                    "and pronunciation as far as the transcript suggests), and language_use.",
    },
    "toefl_speaking_interview": {
        "label": "TOEFL Speaking – Take an Interview",
        "dimensions": ["delivery", "language_use", "topic_development"],
        "scale": "1-6",
        "guidance": "This is the 2026 TOEFL 'Take an Interview' speaking task. The RESPONSE is a "
                    "transcript of a spoken answer to an interview-style question. Judge delivery "
                    "(fluency/clarity implied by the transcript), language use (grammar, vocabulary), "
                    "and topic development (relevance, progression and completeness of ideas).",
    },
    "gre_issue": {
        "label": "GRE Analytical Writing – Issue",
        "dimensions": ["analysis", "support", "organization", "language"],
        "scale": "0-6",
        "guidance": "Judge the cogency of the position on the issue, the quality of reasons and "
                    "examples, organization, and control of language.",
    },
    "gre_argument": {
        "label": "GRE Analytical Writing – Argument",
        "dimensions": ["analysis", "support", "organization", "language"],
        "scale": "0-6",
        "guidance": "Judge how well the response identifies and analyzes the argument's logical "
                    "flaws and assumptions (do NOT reward agreeing/disagreeing), plus support, "
                    "organization, and language.",
    },
}

# Suggested machine-readable weakness tags (Claude may add others, snake_case).
WEAKNESS_TAXONOMY = [
    "connector_monotony", "underdeveloped_argument", "unclear_thesis",
    "weak_topic_sentences", "insufficient_examples", "tense_error",
    "subject_verb_agreement", "article_misuse", "preposition_error",
    "vocabulary_repetition", "awkward_phrasing", "run_on_sentences",
    "sentence_fragments", "off_topic", "redundancy", "informal_tone",
    "missing_words", "wrong_register", "incomplete_task",
]

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class GraderError(Exception):
    pass


def build_prompt(task_type: str, prompt: str | None, user_answer: str) -> str:
    spec = TASK_SPECS[task_type]
    dims = spec["dimensions"]
    breakdown_keys = ", ".join(f'"{d}": <number>' for d in dims)
    return f"""You are an experienced {spec['label']} rater. Grade the response below \
strictly against the official rubric.

{spec['guidance']}
Score scale for the overall score and every dimension: {spec['scale']}.

TASK TYPE: {spec['label']}
PROMPT / QUESTION:
\"\"\"{prompt or '(not provided)'}\"\"\"

TEST-TAKER RESPONSE:
\"\"\"{user_answer}\"\"\"

Return ONLY a single JSON object (no markdown, no commentary) with EXACTLY these keys:
{{
  "score_overall": <number on the {spec['scale']} scale>,
  "breakdown": {{ {breakdown_keys} }},
  "problem_sentences": [
     {{ "original": "<quote from the response>", "issue": "<short reason, in 繁體中文>", "rewrite": "<improved English version>" }}
  ],
  "weaknesses": [<1-5 snake_case tags; prefer these where they fit: {", ".join(WEAKNESS_TAXONOMY)}>],
  "model_high_score_version": "<a full high-scoring rewrite of the whole response, in English>",
  "summary_zh": "<繁體中文總評與下一步具體建議, 3-5 句>"
}}

Rules:
- Output valid JSON and nothing else. Do not wrap it in code fences.
- Include 2-5 items in problem_sentences when the response is long enough.
- "issue" and "summary_zh" must be in Traditional Chinese; English fields stay in English.
"""


def parse_feedback(text: str) -> dict:
    """Tolerant JSON extraction: strip fences, slice to the outermost object."""
    cleaned = FENCE_RE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise GraderError("no JSON object found in model output")
    return json.loads(cleaned[start:end + 1])


def normalize_feedback(data: dict) -> dict:
    """Coerce to the shape the frontend/schema expects, tolerating minor drift."""
    breakdown = {}
    for k, v in (data.get("breakdown") or {}).items():
        try:
            breakdown[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    problems = []
    for p in (data.get("problem_sentences") or []):
        if isinstance(p, dict):
            problems.append({
                "original": str(p.get("original", "")),
                "issue": str(p.get("issue", "")),
                "rewrite": str(p.get("rewrite", "")),
            })
    weaknesses = [re.sub(r"[^a-z0-9_]", "", str(w).strip().lower().replace(" ", "_"))
                  for w in (data.get("weaknesses") or [])]
    weaknesses = [w for w in weaknesses if w]
    score = data.get("score_overall")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None
    return {
        "score_overall": score,
        "breakdown": breakdown,
        "problem_sentences": problems,
        "weaknesses": weaknesses,
        "model_high_score_version": str(data.get("model_high_score_version", "")),
        "summary_zh": str(data.get("summary_zh", "")),
    }


def _call_claude(prompt_text: str) -> str:
    """Single Claude API call returning raw text. Patched out in tests."""
    import anthropic
    if not settings.anthropic_api_key:
        raise GraderError("ANTHROPIC_API_KEY 未設定 (在 backend/.env 填入)")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt_text}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")


def grade(task_type: str, prompt: str | None, user_answer: str) -> dict:
    if task_type not in TASK_SPECS:
        raise GraderError(f"unknown task_type: {task_type}")
    if not (user_answer or "").strip():
        raise GraderError("作答內容是空的")

    prompt_text = build_prompt(task_type, prompt, user_answer)
    last_err: Exception | None = None
    for _ in range(2):  # one retry on parse failure
        raw = _call_claude(prompt_text)
        try:
            return normalize_feedback(parse_feedback(raw))
        except (GraderError, json.JSONDecodeError) as e:
            last_err = e
    raise GraderError(f"無法解析批改結果: {last_err}")
