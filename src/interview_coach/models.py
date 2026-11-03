"""Domain models for the interview coach: questions, answers, transcripts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Difficulty(str, Enum):
    """Question difficulty. Values sort easy -> hard."""

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"

    @classmethod
    def from_str(cls, value: str) -> Difficulty:
        try:
            return cls(value.strip().lower())
        except ValueError:
            allowed = ", ".join(d.value for d in cls)
            raise ValueError(f"unknown difficulty {value!r}; expected one of: {allowed}") from None


@dataclass(frozen=True)
class Question:
    """A single interview question from the bank.

    ``ideal_points`` are the points a strong answer should cover; the
    scoring engine (next session) uses them to grade answers. They are
    deliberately short phrases, not a model answer, so feedback stays
    about coverage rather than wording.
    """

    id: str
    text: str
    category: str
    difficulty: Difficulty = Difficulty.MID
    ideal_points: tuple[str, ...] = ()
    follow_ups: tuple[str, ...] = ()
    time_limit_seconds: int | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("question id must not be empty")
        if not self.text.strip():
            raise ValueError("question text must not be empty")
        if not self.category.strip():
            raise ValueError("question category must not be empty")
        if self.time_limit_seconds is not None and self.time_limit_seconds <= 0:
            raise ValueError("time_limit_seconds must be positive when set")
        if isinstance(self.difficulty, str):  # tolerate plain strings at construction
            object.__setattr__(self, "difficulty", Difficulty.from_str(self.difficulty))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "category": self.category,
            "difficulty": self.difficulty.value,
            "ideal_points": list(self.ideal_points),
            "follow_ups": list(self.follow_ups),
            "time_limit_seconds": self.time_limit_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Question:
        try:
            return cls(
                id=str(data["id"]),
                text=str(data["text"]),
                category=str(data["category"]),
                difficulty=Difficulty.from_str(str(data.get("difficulty", "mid"))),
                ideal_points=tuple(str(p) for p in data.get("ideal_points", [])),
                follow_ups=tuple(str(f) for f in data.get("follow_ups", [])),
                time_limit_seconds=data.get("time_limit_seconds"),
            )
        except KeyError as exc:
            raise ValueError(f"question entry is missing required field {exc.args[0]!r}") from exc


@dataclass
class Answer:
    """One recorded answer inside a session transcript."""

    question_id: str
    text: str
    elapsed_seconds: float
    skipped: bool = False

    def __post_init__(self) -> None:
        if self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must not be negative")

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "text": self.text,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "skipped": self.skipped,
        }


@dataclass
class SessionResult:
    """The finished transcript of one mock interview."""

    questions: list[Question] = field(default_factory=list)
    answers: list[Answer] = field(default_factory=list)
    total_seconds: float = 0.0

    @property
    def answered(self) -> list[Answer]:
        return [a for a in self.answers if not a.skipped]

    @property
    def skipped(self) -> list[Answer]:
        return [a for a in self.answers if a.skipped]

    @property
    def answer_by_id(self) -> dict[str, Answer]:
        return {a.question_id: a for a in self.answers}

    def to_dict(self) -> dict:
        return {
            "questions": [q.to_dict() for q in self.questions],
            "answers": [a.to_dict() for a in self.answers],
            "total_seconds": round(self.total_seconds, 2),
            "answered_count": len(self.answered),
            "skipped_count": len(self.skipped),
        }
