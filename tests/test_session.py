import pytest

from interview_coach.bank import load_bank
from interview_coach.session import InterviewSession, SessionConfig, SessionStateError


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture()
def bank():
    return load_bank()


def test_full_session_records_answers_and_timing(bank):
    clock = FakeClock()
    session = InterviewSession(bank, SessionConfig(question_count=2, seed=3), clock=clock)
    first = session.start()
    assert session.current_question is first
    assert session.position == (1, 2)
    clock.advance(30)
    second = session.answer("first answer")
    assert second is not None
    assert session.current_question is second
    assert session.position == (2, 2)
    clock.advance(45)
    assert session.skip() is None
    result = session.result()
    assert len(result.answered) == 1
    assert len(result.skipped) == 1
    assert result.answers[0].elapsed_seconds == pytest.approx(30)
    assert result.answers[1].skipped
    assert result.total_seconds == pytest.approx(75)


def test_session_state_errors(bank):
    session = InterviewSession(bank, SessionConfig(question_count=1, seed=1))
    with pytest.raises(SessionStateError):
        session.answer("too early")
    with pytest.raises(SessionStateError):
        session.finish()
    session.start()
    with pytest.raises(SessionStateError):
        session.start()
    with pytest.raises(ValueError):
        session.answer("   ")
    session.skip()
    with pytest.raises(SessionStateError):
        session.answer("too late")


def test_empty_pool_raises_on_start(bank):
    session = InterviewSession(bank, SessionConfig(question_count=3, category="nonexistent"))
    with pytest.raises(SessionStateError):
        session.start()


def test_category_filter_and_seed_reproducibility(bank):
    a = InterviewSession(bank, SessionConfig(question_count=3, category="python", seed=9))
    b = InterviewSession(bank, SessionConfig(question_count=3, category="python", seed=9))
    assert a.start().id == b.start().id
    assert a.current_question.category == "python"


def test_finish_early_keeps_partial_transcript(bank):
    session = InterviewSession(bank, SessionConfig(question_count=5, seed=2))
    session.start()
    session.answer("only this one")
    result = session.finish()
    assert len(result.answers) == 1
    assert len(result.questions) == 5
    assert session.is_finished
    with pytest.raises(SessionStateError):
        session.finish()


def test_config_rejects_non_positive_count():
    with pytest.raises(ValueError):
        SessionConfig(question_count=0)
