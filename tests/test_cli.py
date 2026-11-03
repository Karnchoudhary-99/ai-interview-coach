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


def test_score_command_scores_a_transcript(monkeypatch, capsys, tmp_path):
    answers = iter(["my answer", "skip"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    transcript = tmp_path / "transcript.json"
    report = tmp_path / "report.md"
    main(["practice", "--count", "2", "--seed", "5", "--transcript", str(transcript)])
    capsys.readouterr()
    assert main(["score", "--transcript", str(transcript), "--report", str(report)]) == 0
    out = capsys.readouterr().out
    assert "Interview feedback" in out
    assert "# Interview feedback" in report.read_text(encoding="utf-8")


def test_score_command_rejects_missing_transcript(capsys, tmp_path):
    assert main(["score", "--transcript", str(tmp_path / "nope.json")]) == 1
    assert "not found" in capsys.readouterr().err


def test_practice_command_writes_report(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("builtins.input", lambda _prompt: "my answer")
    report = tmp_path / "report.md"
    assert main(["practice", "--count", "1", "--seed", "5", "--report", str(report)]) == 0
    assert "# Interview feedback" in report.read_text(encoding="utf-8")


def test_practice_command_handles_eof(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError))
    assert main(["practice", "--count", "2", "--seed", "5"]) == 0
    assert "finishing early" in capsys.readouterr().out
