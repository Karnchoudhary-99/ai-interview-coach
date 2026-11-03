import json

from interview_coach.cli import main


def test_voice_check_reports_backends(monkeypatch, capsys):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    assert main(["voice", "--check"]) == 0
    out = capsys.readouterr().out
    assert "System TTS engines: none found" in out
    assert "Speech recognition bundled: no" in out


def test_voice_say_uses_print_fallback(monkeypatch, capsys):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    assert main(["voice", "--say", "hello there"]) == 0
    assert "[voice] hello there" in capsys.readouterr().out


def test_voice_say_system_without_engine_fails(monkeypatch, capsys):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    assert main(["voice", "--say", "hi", "--voice-output", "system"]) == 1
    assert "no system text-to-speech" in capsys.readouterr().err


def test_voice_listen_echoes_typed_line(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: "my answer")
    assert main(["voice", "--listen"]) == 0
    assert "Heard: my answer" in capsys.readouterr().out


def test_practice_voice_mode_speaks_questions(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    answers = iter(["my answer", "skip"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    transcript = tmp_path / "transcript.json"
    assert (
        main(
            [
                "practice", "--count", "2", "--seed", "5",
                "--voice", "--voice-output", "print",
                "--transcript", str(transcript),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Voice mode on (output: print" in out
    assert "[voice] Tell me about a time" in out  # seed 5 asks this question first
    assert out.count("[voice]") >= 3  # two questions + done summary
    data = json.loads(transcript.read_text(encoding="utf-8"))
    assert data["answered_count"] == 1 and data["skipped_count"] == 1


def test_practice_voice_mode_eof_finishes_early(monkeypatch, capsys):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError))
    assert main(["practice", "--count", "2", "--seed", "5", "--voice"]) == 0
    assert "finishing early" in capsys.readouterr().out
