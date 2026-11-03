from interview_coach.voice import ConsoleVoiceInput, ScriptedVoiceInput, describe_voice


def test_scripted_input_yields_lines_then_none():
    source = ScriptedVoiceInput(["  first answer ", "second"])
    assert source.name == "scripted"
    assert source.listen() == "first answer"
    assert source.listen("prompt: ") == "second"
    assert source.listen() is None
    assert source.listen() is None


def test_console_input_strips_and_handles_eof(monkeypatch):
    answers = iter(["  hello  "])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert ConsoleVoiceInput().listen("Say: ") == "hello"


def test_console_input_returns_none_on_eof(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError))
    assert ConsoleVoiceInput().listen() is None


def test_describe_voice_reports_no_bundled_stt(monkeypatch):
    monkeypatch.setattr("interview_coach.voice.shutil.which", lambda _name: None)
    info = describe_voice()
    assert info["system_tts_available"] is False
    assert info["system_tts_engines"] == []
    assert info["speech_recognition_bundled"] is False
    assert info["print_fallback_available"] is True
