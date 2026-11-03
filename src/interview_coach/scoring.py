"""Answer scoring: grade an answer against a question's ideal points.

The scorer is deliberately offline and deterministic — no LLM call, no
network — so a practice session can be graded instantly and
reproducibly. An ideal point is a short phrase ("shows listening to the
other view"); it counts as covered when the answer's words evidence
most of its content words. Coverage, not wording, is what is scored:
synonyms are not recognised, which the report states honestly, and
missed points are reported verbatim so the candidate knows exactly
what to add next time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Answer, Question, SessionResult

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Words that carry no evidence about a point on their own. This includes
# the rubric's framing verbs ("shows", "describes", "explains"): a point
# is about its content words, not about the verb that introduces it, so
# "shows listening to the other view" is graded on listening/other/view.
STOPWORDS = frozenset(
    {
        "shows", "show", "describes", "describe", "explains", "explain",
        "states", "state", "names", "name", "gives", "give", "discusses",
        "discuss", "mentions", "mention", "covers", "cover", "includes",
        "include", "identifies", "identify",
    }
    |
    frozenset(
    {
        "a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "with",
        "by", "at", "from", "is", "are", "was", "were", "be", "been", "it",
        "its", "that", "this", "these", "those", "as", "so", "if", "then",
        "i", "we", "you", "he", "she", "they", "my", "our", "your", "their",
        "me", "us", "him", "her", "them", "do", "does", "did", "have", "has",
        "had", "will", "would", "can", "could", "should", "about", "into",
        "over", "under", "after", "before", "when", "while", "how", "what",
        "which", "who", "whom", "not", "no", "yes", "but", "also",
    }
    )
)

# A point counts as covered when at least this fraction of its content
# words are evidenced in the answer. 0.6 (not 1.0) tolerates paraphrase:
# "listened to their concerns" evidences "shows listening to the other
# view" via listening/listened and view-adjacent words, without needing
# every filler word to match.
COVERAGE_THRESHOLD = 0.6


def _stem(word: str) -> str:
    """Light stem: strip common suffixes so inflections match.

    Only the tail is touched, and only for words long enough that the
    stem stays meaningful ("listening" -> "listen", "disagreed" ->
    "disagre"). Irregular forms are left alone; the prefix-match in
    _evidenced covers the rest.
    """
    if len(word) > 5 and word.endswith("ing"):
        word = word[:-3]
        if len(word) > 2 and word[-1] == word[-2]:
            word = word[:-1]
    elif len(word) > 4 and word.endswith("ed"):
        word = word[:-2]
    elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    """Lowercased, stemmed content tokens of ``text`` (stopwords removed)."""
    return [_stem(tok) for tok in _TOKEN_RE.findall(text.lower()) if tok not in STOPWORDS]


def _evidenced(point_token: str, answer_tokens: set[str]) -> bool:
    """True when an answer token evidences a point token.

    Exact stem matches count, as do prefix matches of at least 4
    characters ("disagre" evidences "disagreement" and vice versa),
    which catches the noun/verb pairs ideal points commonly use.
    """
    if point_token in answer_tokens:
        return True
    for token in answer_tokens:
        if len(token) >= 4 and len(point_token) >= 4 and (
            token.startswith(point_token) or point_token.startswith(token)
        ):
            return True
    return False


def point_coverage(point: str, answer_text: str) -> float:
    """Fraction of a point's content words evidenced in the answer text."""
    point_tokens = tokenize(point)
    if not point_tokens:
        return 1.0  # a point with no content words cannot be missed
    answer_tokens = set(tokenize(answer_text))
    if not answer_tokens:
        return 0.0
    matched = sum(1 for tok in point_tokens if _evidenced(tok, answer_tokens))
    return matched / len(point_tokens)


def point_covered(point: str, answer_text: str) -> bool:
    """True when an ideal point is covered by the answer text."""
    return point_coverage(point, answer_text) >= COVERAGE_THRESHOLD


@dataclass(frozen=True)
class QuestionScore:
    """Score for one question in a session."""

    question: Question
    answer: Answer | None  # None when the question was never reached
    score: float  # 0-100
    covered_points: tuple[str, ...] = ()
    missed_points: tuple[str, ...] = ()
    over_time_limit: bool = False

    @property
    def skipped(self) -> bool:
        return self.answer is not None and self.answer.skipped

    @property
    def band(self) -> str:
        """Human-readable band for the score."""
        return score_band(self.score)

    def to_dict(self) -> dict:
        return {
            "question_id": self.question.id,
            "category": self.question.category,
            "difficulty": self.question.difficulty.value,
            "score": round(self.score, 1),
            "band": self.band,
            "skipped": self.skipped,
            "answered": self.answer is not None and not self.answer.skipped,
            "elapsed_seconds": round(self.answer.elapsed_seconds, 2) if self.answer else None,
            "over_time_limit": self.over_time_limit,
            "covered_points": list(self.covered_points),
            "missed_points": list(self.missed_points),
        }


def score_band(score: float) -> str:
    """Band label for a 0-100 score."""
    if score >= 80:
        return "strong"
    if score >= 50:
        return "developing"
    return "needs work"


def score_question(question: Question, answer: Answer | None) -> QuestionScore:
    """Score one question against its answer (or lack of one)."""
    if answer is None or answer.skipped:
        return QuestionScore(
            question=question,
            answer=answer,
            score=0.0,
            covered_points=(),
            missed_points=tuple(question.ideal_points),
        )
    if not question.ideal_points:
        # No rubric to grade against: a non-empty answer gets full marks
        # rather than being penalised for a bank entry with no points.
        return QuestionScore(question=question, answer=answer, score=100.0)
    covered = tuple(p for p in question.ideal_points if point_covered(p, answer.text))
    missed = tuple(p for p in question.ideal_points if p not in covered)
    score = 100.0 * len(covered) / len(question.ideal_points)
    over_time = (
        question.time_limit_seconds is not None
        and answer.elapsed_seconds > question.time_limit_seconds
    )
    return QuestionScore(
        question=question,
        answer=answer,
        score=score,
        covered_points=covered,
        missed_points=missed,
        over_time_limit=over_time,
    )


@dataclass
class SessionScore:
    """Scores for a whole session, with per-category aggregates."""

    per_question: list[QuestionScore] = field(default_factory=list)
    total_seconds: float = 0.0

    @property
    def overall(self) -> float:
        """Mean over every question in the session (skipped/unreached = 0)."""
        if not self.per_question:
            return 0.0
        return sum(q.score for q in self.per_question) / len(self.per_question)

    @property
    def answered_only(self) -> float:
        """Mean over answered questions only; 0.0 when none were answered."""
        answered = [q for q in self.per_question if q.answer is not None and not q.answer.skipped]
        if not answered:
            return 0.0
        return sum(q.score for q in answered) / len(answered)

    @property
    def band(self) -> str:
        return score_band(self.overall)

    @property
    def skipped_count(self) -> int:
        return sum(1 for q in self.per_question if q.skipped)

    @property
    def unanswered_count(self) -> int:
        return sum(1 for q in self.per_question if q.answer is None)

    @property
    def over_time_count(self) -> int:
        return sum(1 for q in self.per_question if q.over_time_limit)

    def category_scores(self) -> dict[str, float]:
        """Mean score per category, in first-seen order."""
        totals: dict[str, list[float]] = {}
        for item in self.per_question:
            totals.setdefault(item.question.category, []).append(item.score)
        return {cat: sum(scores) / len(scores) for cat, scores in totals.items()}

    def to_dict(self) -> dict:
        return {
            "overall": round(self.overall, 1),
            "answered_only": round(self.answered_only, 1),
            "band": self.band,
            "total_seconds": round(self.total_seconds, 2),
            "answered_count": len(self.per_question) - self.skipped_count - self.unanswered_count,
            "skipped_count": self.skipped_count,
            "unanswered_count": self.unanswered_count,
            "over_time_count": self.over_time_count,
            "category_scores": {k: round(v, 1) for k, v in self.category_scores().items()},
            "per_question": [q.to_dict() for q in self.per_question],
        }


def score_session(result: SessionResult) -> SessionScore:
    """Score every question in a finished session transcript."""
    by_id = result.answer_by_id
    per_question = [score_question(q, by_id.get(q.id)) for q in result.questions]
    return SessionScore(per_question=per_question, total_seconds=result.total_seconds)
