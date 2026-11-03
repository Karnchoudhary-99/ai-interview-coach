import json

from interview_coach.cli import main


def test_bank_command_lists_filtered_questions(capsys):
    assert main(["bank", "--category", "python", "--difficulty", "junior"]) == 0
    out = capsys.readouterr().out
    assert "[py-01]" in out and "[py-02]" in out
    assert "[beh-01]" not in out


def test_bank_command_reports_no_matches(capsys):
    assert main(["bank", "--category", "nope"]) == 0
    assert "No questions match" in capsys.readouterr().out


def test_practice_command_runs_from_stdin(monkeypatch, capsys, tmp_path):
    answers = iter(["my answer", "skip"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    transcript = tmp_path / "transcript.json"
    assert (
        main(["practice", "--count", "2", "--seed", "5", "--transcript", str(transcript)]) == 0
    )
    out = capsys.readouterr().out
    assert "1 answered, 1 skipped" in out
    data = json.loads(transcript.read_text(encoding="utf-8"))
    assert data["answered_count"] == 1
    assert data["skipped_count"] == 1
    assert len(data["questions"]) == 2


def test_practice_command_handles_eof(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError))
    assert main(["practice", "--count", "2", "--seed", "5"]) == 0
    assert "finishing early" in capsys.readouterr().out
