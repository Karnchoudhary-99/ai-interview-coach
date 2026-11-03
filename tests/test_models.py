import pytest

from interview_coach.models import Answer, Difficulty, Question, SessionResult


def test_question_requires_text_and_category():
    with pytest.raises(ValueError):
        Question(id="q1", text="  ", category="behavioral")
    with pytest.raises(ValueError):
        Question(id="q1", text="Why?", category="  ")


def test_question_accepts_plain_string_difficulty():
    question = Question(id="q1", text="Why?", category="python", difficulty="senior")
    assert question.difficulty is Difficulty.SENIOR


def test_question_rejects_bad_difficulty_and_time_limit():
    with pytest.raises(ValueError):
        Question(id="q1", text="Why?", category="python", difficulty="expert")
    with pytest.raises(ValueError):
        Question(id="q1", text="Why?", category="python", time_limit_seconds=0)


def test_question_round_trip_through_dict():
    question = Question(
        id="q1",
        text="Why?",
        category="python",
        difficulty=Difficulty.MID,
        ideal_points=("a", "b"),
        follow_ups=("And then?",),
        time_limit_seconds=120,
    )
    restored = Question.from_dict(question.to_dict())
    assert restored == question


def test_question_from_dict_requires_core_fields():
    with pytest.raises(ValueError):
        Question.from_dict({"id": "q1", "text": "Why?"})


def test_answer_rejects_negative_elapsed():
    with pytest.raises(ValueError):
        Answer(question_id="q1", text="x", elapsed_seconds=-1.0)


def test_session_result_counts_and_lookup():
    questions = [Question(id="q1", text="A?", category="c"), Question(id="q2", text="B?", category="c")]
    result = SessionResult(
        questions=questions,
        answers=[
            Answer("q1", "answer", 10.0),
            Answer("q2", "", 5.0, skipped=True),
        ],
        total_seconds=15.0,
    )
    assert len(result.answered) == 1
    assert len(result.skipped) == 1
    assert result.answer_by_id["q1"].text == "answer"
    assert result.to_dict()["answered_count"] == 1
