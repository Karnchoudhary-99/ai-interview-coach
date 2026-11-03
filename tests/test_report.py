import json

import pytest

from interview_coach.models import Answer, Question, SessionResult
from interview_coach.report import (
    action_items,
    load_transcript,
    render_markdown,
    render_text,
    strengths_and_gaps,
)
from interview_coach.scoring import score_session


def _result():
    questions = [
        Question(
            id="q1", text="Disagreement?", category="behavioral",
            ideal_points=("describes the disagreement concretely", "shows listening"),
        ),
        Question(
            id="q2", text="Hash map?", category="algorithms",
            ideal_points=("explains constant-time lookup",),
        ),
        Question(id="q3", text="Unreached?", category="system design", ideal_points=("names a project",)),
    ]
    return SessionResult(
        questions=questions,
        answers=[
            Answer("q1", "We disagreed concretely. I listened.", 60),
            Answer("q2", "", 5, skipped=True),
        ],
        total_seconds=65,
    )


def test_strengths_gaps_and_action_items():
    scored = score_session(_result())
    strengths, gaps = strengths_and_gaps(scored)
    assert strengths == ["behavioral"]  # q1 fully covered, alone in its category
    assert gaps == ["algorithms", "system design"]  # skipped q2, unreached q3


def test_action_items_name_missed_points_and_skips():
    scored = score_session(_result())
    items = action_items(scored)
    assert any("Answer q2 instead of skipping" in item for item in items)
    assert any("Reach q3" in item for item in items)


def test_renderers_include_scores_and_limit_note():
    scored = score_session(_result())
    text = render_text(scored)
    markdown = render_markdown(scored)
    assert "overall" in text.lower()
    assert "# Interview feedback" in markdown
    assert "word-coverage" in text
    assert "word-coverage" in markdown
    assert "q1" in text and "q2" in markdown


def test_load_transcript_round_trip(tmp_path):
    result = _result()
    path = tmp_path / "transcript.json"
    path.write_text(json.dumps(result.to_dict()), encoding="utf-8")
    loaded = load_transcript(str(path))
    assert loaded.total_seconds == result.total_seconds
    assert [q.id for q in loaded.questions] == ["q1", "q2", "q3"]
    assert loaded.answers[1].skipped
    assert score_session(loaded).overall == score_session(result).overall


def test_load_transcript_rejects_bad_files(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(ValueError, match="not found"):
        load_transcript(str(missing))
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_transcript(str(bad))
    wrong_shape = tmp_path / "shape.json"
    wrong_shape.write_text(json.dumps({"answers": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected shape"):
        load_transcript(str(wrong_shape))
