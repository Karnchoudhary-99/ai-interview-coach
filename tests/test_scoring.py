import pytest

from interview_coach.models import Answer, Question, SessionResult
from interview_coach.scoring import (
    point_coverage,
    point_covered,
    score_band,
    score_question,
    score_session,
    tokenize,
)


def _question(**kwargs):
    defaults = {
        "id": "q1",
        "text": "Tell me about a disagreement.",
        "category": "behavioral",
        "ideal_points": (
            "describes the disagreement concretely",
            "shows listening to the other view",
            "explains the resolution and its outcome",
        ),
    }
    defaults.update(kwargs)
    return Question(**defaults)


def test_tokenize_stems_and_drops_stopwords():
    assert "listen" in tokenize("I was listening carefully")
    assert tokenize("the and of") == []


def test_point_covered_by_paraphrase_prefix():
    # "listened" evidences "listening" via stemming; disagreement/disagree via prefix.
    assert point_covered(
        "shows listening to the other view",
        "I listened to their view and understood their concerns.",
    )
    assert point_covered(
        "describes the disagreement concretely",
        "We disagreed concretely about the database choice.",
    )


def test_point_not_covered_by_unrelated_answer():
    assert not point_covered(
        "explains the resolution and its outcome",
        "I like pizza and weekends.",
    )
    assert point_coverage("explains the resolution and its outcome", "") == 0.0


def test_score_question_partial_credit():
    question = _question()
    answer = Answer(
        "q1",
        "We disagreed concretely about the API design. I listened to their view.",
        60,
    )
    scored = score_question(question, answer)
    assert scored.score == pytest.approx(100 * 2 / 3)
    assert len(scored.covered_points) == 2
    assert len(scored.missed_points) == 1
    assert scored.band == "developing"


def test_score_question_skipped_and_unreached_are_zero():
    question = _question()
    skipped = score_question(question, Answer("q1", "", 10, skipped=True))
    assert skipped.score == 0.0 and skipped.skipped
    assert skipped.missed_points == question.ideal_points
    unreached = score_question(question, None)
    assert unreached.score == 0.0 and not unreached.skipped


def test_score_question_no_ideal_points_does_not_penalise():
    question = _question(ideal_points=())
    assert score_question(question, Answer("q1", "anything", 10)).score == 100.0


def test_score_question_over_time_limit_flag():
    question = _question(time_limit_seconds=60)
    assert score_question(question, Answer("q1", "We disagreed.", 61)).over_time_limit
    assert not score_question(question, Answer("q1", "We disagreed.", 60)).over_time_limit


def test_score_band_boundaries():
    assert score_band(80) == "strong"
    assert score_band(79.9) == "developing"
    assert score_band(50) == "developing"
    assert score_band(49.9) == "needs work"


def test_score_session_aggregates_and_categories():
    questions = [
        _question(id="q1", category="behavioral"),
        _question(
            id="q2",
            text="What is a hash map?",
            category="algorithms",
            ideal_points=("explains constant-time lookup",),
        ),
        _question(id="q3", category="behavioral"),
    ]
    result = SessionResult(
        questions=questions,
        answers=[
            Answer("q1", "We disagreed concretely. I listened to their view.", 60),
            Answer("q2", "A hash map gives constant-time lookup.", 30),
            Answer("q3", "", 5, skipped=True),
        ],
        total_seconds=95,
    )
    scored = score_session(result)
    assert len(scored.per_question) == 3
    assert scored.skipped_count == 1
    assert scored.overall == pytest.approx(sum(q.score for q in scored.per_question) / 3)
    assert scored.answered_only > scored.overall  # skipped 0 drags the overall down
    assert scored.category_scores()["algorithms"] == 100.0
    assert scored.to_dict()["band"] == scored.band
