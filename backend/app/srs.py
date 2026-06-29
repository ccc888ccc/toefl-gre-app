"""SM-2 spaced-repetition algorithm (same family as Anki), per spec section 3.1.

Four self-grades map onto SM-2 quality scores:
    again = 2 (fail)   hard = 3   good = 4   easy = 5

Rules:
  - Pass (hard/good/easy): repetitions += 1
        rep == 1 -> interval = 1 day
        rep == 2 -> interval = 6 days
        rep >= 3 -> interval = round(prev_interval * ease_factor)
    'hard' shortens the resulting interval, 'easy' lengthens it.
  - Fail (again): repetitions -> 0, interval -> 1 day.
  - ease_factor adjusts every review, floored at 1.3.
"""
from dataclasses import dataclass

GRADE_Q = {"again": 2, "hard": 3, "good": 4, "easy": 5}
EASE_FLOOR = 1.3
HARD_FACTOR = 0.8
EASY_BONUS = 1.3


@dataclass
class Sm2Result:
    ease_factor: float
    interval_days: int
    repetitions: int
    correct: bool


def update_sm2(ease_factor: float, interval_days: int, repetitions: int, grade: str) -> Sm2Result:
    if grade not in GRADE_Q:
        raise ValueError(f"invalid grade: {grade!r}")
    q = GRADE_Q[grade]
    correct = q >= 3

    # Standard SM-2 ease-factor update.
    ease_factor = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if ease_factor < EASE_FLOOR:
        ease_factor = EASE_FLOOR

    if not correct:                       # again
        repetitions = 0
        interval_days = 1
    else:
        repetitions += 1
        if repetitions == 1:
            interval_days = 1
        elif repetitions == 2:
            interval_days = 6
        else:
            interval_days = round(interval_days * ease_factor)
        if grade == "hard":
            interval_days = round(interval_days * HARD_FACTOR)
        elif grade == "easy":
            interval_days = round(interval_days * EASY_BONUS)

    interval_days = max(1, int(interval_days))
    return Sm2Result(round(ease_factor, 4), interval_days, repetitions, correct)
