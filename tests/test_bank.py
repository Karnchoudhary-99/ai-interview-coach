import json

import pytest

from interview_coach.bank import categories, filter_bank, load_bank, select_questions
from interview_coach.models import Difficulty, Question


def test_bundled_bank_loads_and_covers_categories():
    questions = load_bank()
    assert len(questions) == 30
    assert set(categories(questions)) == {"behavioral", "algorithms", "system-design", "python", "databases"}
    assert all(q.ideal_points for q in questions)
    assert len({q.id for q in questions}) == 30


def test_filter_bank_by_category_and_difficulty():
    questions = load_bank()
    senior = filter_bank(questions, difficulty=Difficulty.SENIOR)
    assert senior and all(q.difficulty is Difficulty.SENIOR for q in senior)
    assert filter_bank(questions, category="python", difficulty="junior")
    assert filter_bank(questions, category="nope") == []


def test_select_questions_is_seeded_and_repeat_free():
    questions = load_bank()
    first = select_questions(questions, 5, seed=7)
    second = select_questions(questions, 5, seed=7)
    assert [q.id for q in first] == [q.id for q in second]
    assert len({q.id for q in first}) == 5
    assert len(select_questions(questions, 999)) == len(questions)


def test_select_questions_rejects_negative_count():
    with pytest.raises(ValueError):
        select_questions(load_bank(), -1)


def test_load_bank_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "bank.json"
    entry = {"id": "dup", "text": "A?", "category": "c"}
    path.write_text(json.dumps([entry, entry]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_bank(path)


def test_load_bank_rejects_bad_json_and_missing_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_bank(bad)
    with pytest.raises(ValueError):
        load_bank(tmp_path / "missing.json")
    not_a_list = tmp_path / "obj.json"
    not_a_list.write_text(json.dumps({"id": "x"}), encoding="utf-8")
    with pytest.raises(TypeError):
        load_bank(not_a_list)


def test_load_bank_accepts_custom_file(tmp_path):
    path = tmp_path / "bank.json"
    path.write_text(
        json.dumps([{"id": "c1", "text": "Custom?", "category": "custom", "difficulty": "mid"}]),
        encoding="utf-8",
    )
    questions = load_bank(path)
    assert [q.id for q in questions] == ["c1"]
    assert questions[0].difficulty is Difficulty.MID
    assert Question.from_dict({"id": "x", "text": "T?", "category": "c"}).difficulty is Difficulty.MID
