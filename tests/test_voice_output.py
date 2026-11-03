import subprocess

import pytest

from interview_coach.voice import (
    PrintVoiceOutput,
    SystemVoiceOutput,
    VoiceConfig,
    VoiceError,
    available_tts_engines,
    make_voice_output,
)


def test_print_output_narrates(capsys):
    out = PrintVoiceOutput()
    assert out.available and out.name == "print"
    out.speak("hello")
    assert "[voice] hello" in capsys.readouterr().out


def test_available_engines_empty_without_tts(monkeypatch):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    assert available_tts_engines() == []


def test_system_output_uses_first_engine(monkeypatch):
    monkeypatch.setattr(
        "interview_coach.voice.shutil.which",
        lambda name: f"/usr/bin/{name}" if name == "espeak" else None,
    )
    calls = []
    monkeypatch.setattr(
        "interview_coach.voice.subprocess.run",
        lambda argv, check: calls.append(argv),
    )
    out = SystemVoiceOutput(rate=120)
    assert out.name == "espeak"
    out.speak("hello")
    assert calls == [["espeak", "-s", "120", "hello"]]


def test_system_output_failure_becomes_voice_error(monkeypatch):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: "/usr/bin/say")
    monkeypatch.setattr(
        "interview_coach.voice.subprocess.run",
        lambda argv, check: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, argv)
        ),
    )
    with pytest.raises(VoiceError, match="TTS engine"):
        SystemVoiceOutput().speak("hello")


def test_system_output_requires_an_engine(monkeypatch):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    with pytest.raises(VoiceError, match="no system text-to-speech"):
        SystemVoiceOutput()


def test_system_output_rejects_bad_rate():
    with pytest.raises(ValueError, match="rate"):
        SystemVoiceOutput(rate=10)


def test_make_output_auto_falls_back_to_print(monkeypatch, capsys):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    out = make_voice_output(VoiceConfig(output="auto"))
    assert out.name == "print"
    out.speak("hi")
    assert "[voice] hi" in capsys.readouterr().out


def test_make_output_system_raises_without_engine(monkeypatch):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    with pytest.raises(VoiceError):
        make_voice_output(VoiceConfig(output="system"))


def test_voice_config_rejects_bad_output():
    with pytest.raises(ValueError, match="output"):
        VoiceConfig(output="cloud")
