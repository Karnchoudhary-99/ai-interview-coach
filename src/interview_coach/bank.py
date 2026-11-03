"""Question bank: loading, filtering, and deterministic selection."""

from __future__ import annotations

import json
import random
from importlib import resources
from pathlib import Path

from .models import Difficulty, Question

_BUNDLED_FILENAME = "questions.json"


def _bundled_path() -> Path:
    return Path(str(resources.files("interview_coach") / "data" / _BUNDLED_FILENAME))


def load_bank(path: str | Path | None = None) -> list[Question]:
    """Load questions from a JSON file, or the bundled bank when ``path`` is None.

    The file holds a JSON list of question objects (see
    :meth:`Question.from_dict`). Duplicate ids and non-list payloads are
    rejected so a bad bank file fails loudly instead of silently
    dropping questions mid-interview.
    """
    source = Path(path) if path is not None else _bundled_path()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"question bank file not found: {source}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"question bank file is not valid JSON: {source} ({exc})") from None
    if not isinstance(raw, list):
        raise ValueError(f"question bank must be a JSON list, got {type(raw).__name__}")
    questions = [Question.from_dict(entry) for entry in raw]
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            raise ValueError(f"duplicate question id in bank: {question.id!r}")
        seen.add(question.id)
    return questions


def categories(questions: list[Question]) -> list[str]:
    """Category names present in the bank, in first-seen order."""
    ordered: list[str] = []
    for question in questions:
        if question.category not in ordered:
            ordered.append(question.category)
    return ordered


def filter_bank(
    questions: list[Question],
    *,
    category: str | None = None,
    difficulty: Difficulty | str | None = None,
) -> list[Question]:
    """Filter by category and/or difficulty; unknown filters yield an empty list."""
    wanted = Difficulty.from_str(difficulty) if isinstance(difficulty, str) else difficulty
    return [
        q
        for q in questions
        if (category is None or q.category == category)
        and (wanted is None or q.difficulty == wanted)
    ]


def select_questions(
    questions: list[Question],
    count: int,
    *,
    seed: int | None = None,
) -> list[Question]:
    """Pick up to ``count`` questions in a shuffled order without repeats.

    A fixed ``seed`` reproduces the same selection and order, which is
    what the CLI demo and the tests rely on. Requesting more questions
    than available returns all of them rather than erroring.
    """
    if count < 0:
        raise ValueError("count must not be negative")
    pool = list(questions)
    rng = random.Random(seed)
    rng.shuffle(pool)
    return pool[:count]
