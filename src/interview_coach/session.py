"""Interview session engine: drives one mock interview end to end."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .bank import select_questions
from .models import Answer, Question, SessionResult


@dataclass(frozen=True)
class SessionConfig:
    """How a session is assembled. All fields have safe defaults."""

    question_count: int = 5
    category: str | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.question_count <= 0:
            raise ValueError("question_count must be positive")


class SessionStateError(RuntimeError):
    """Raised when an operation does not fit the session's current state."""


@dataclass
class InterviewSession:
    """State machine for one mock interview.

    Lifecycle: ``start()`` -> ``current_question`` / ``answer()`` /
    ``skip()`` -> ``finish()``. The clock is injectable so tests can
    control elapsed time without sleeping.
    """

    bank: list[Question]
    config: SessionConfig = field(default_factory=SessionConfig)
    clock: object = field(default=time.monotonic, repr=False)  # callable -> float

    _questions: list[Question] = field(default_factory=list, init=False, repr=False)
    _answers: list[Answer] = field(default_factory=list, init=False, repr=False)
    _index: int = field(default=0, init=False, repr=False)
    _started: bool = field(default=False, init=False, repr=False)
    _finished: bool = field(default=False, init=False, repr=False)
    _question_started_at: float = field(default=0.0, init=False, repr=False)
    _session_started_at: float = field(default=0.0, init=False, repr=False)

    def start(self) -> Question:
        if self._started:
            raise SessionStateError("session already started")
        pool = [q for q in self.bank if self.config.category is None or q.category == self.config.category]
        self._questions = select_questions(pool, self.config.question_count, seed=self.config.seed)
        if not self._questions:
            raise SessionStateError("no questions match the session config")
        self._started = True
        self._session_started_at = self.clock()
        self._question_started_at = self._session_started_at
        return self._questions[0]

    @property
    def current_question(self) -> Question | None:
        if not self._started or self._finished or self._index >= len(self._questions):
            return None
        return self._questions[self._index]

    @property
    def position(self) -> tuple[int, int]:
        """(1-based position of the current question, total questions)."""
        return (min(self._index + 1, len(self._questions)), len(self._questions))

    @property
    def is_finished(self) -> bool:
        return self._finished

    def _record(self, text: str, skipped: bool) -> Question | None:
        if not self._started:
            raise SessionStateError("session has not started; call start() first")
        if self._finished or self._index >= len(self._questions):
            self._finished = True
            raise SessionStateError("session is already finished")
        question = self._questions[self._index]
        elapsed = self.clock() - self._question_started_at
        self._answers.append(Answer(question.id, text, elapsed, skipped=skipped))
        self._index += 1
        if self._index >= len(self._questions):
            return None
        self._question_started_at = self.clock()
        return self._questions[self._index]

    def answer(self, text: str) -> Question | None:
        """Record an answer; returns the next question or None if done."""
        if not text.strip():
            raise ValueError("answer text must not be empty (use skip() to pass)")
        return self._record(text, skipped=False)

    def skip(self) -> Question | None:
        """Pass on the current question; returns the next question or None."""
        return self._record("", skipped=True)

    def finish(self) -> SessionResult:
        """End the session early (unanswered questions stay unanswered)."""
        if not self._started:
            raise SessionStateError("session has not started; call start() first")
        if self._finished:
            raise SessionStateError("session is already finished")
        self._finished = True
        return SessionResult(
            questions=list(self._questions),
            answers=list(self._answers),
            total_seconds=self.clock() - self._session_started_at,
        )

    def result(self) -> SessionResult:
        """Transcript so far; finishing is implicit once all questions are answered."""
        if not self._started:
            raise SessionStateError("session has not started; call start() first")
        if self._index >= len(self._questions) and not self._finished:
            self._finished = True
        return SessionResult(
            questions=list(self._questions),
            answers=list(self._answers),
            total_seconds=self.clock() - self._session_started_at,
        )
