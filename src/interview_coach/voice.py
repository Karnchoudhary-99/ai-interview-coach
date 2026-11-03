"""Voice input/output support for mock interviews.

The coach is deliberately dependency-free, so this module does not bundle
a speech-recognition engine or a text-to-speech library. Instead it
defines small ``VoiceOutput`` / ``VoiceInput`` protocols, ships backends
that work with what is already on the machine, and lets a caller plug in
a real STT/TTS implementation later without touching the session engine:

* Output: the system TTS engine (``espeak-ng`` / ``espeak`` / ``say``)
  when one is installed, otherwise a print fallback that narrates the
  session on screen. The fallback is the default on machines (and in CI)
  with no TTS engine, and it is labelled as such — it never pretends
  to be audio.
* Input: no offline STT engine is bundled, so the shipped input backend
  reads a typed line (the honest fallback, documented in the README).
  ``ScriptedVoiceInput`` feeds canned lines for demos and tests, and
  any object with a ``listen(prompt) -> str | None`` method works as a
  custom input backend — e.g. one wrapping Whisper or a cloud STT API.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class VoiceError(RuntimeError):
    """Raised when a requested voice backend cannot run."""


class VoiceOutput(Protocol):
    """Something that can speak a line of text."""

    @property
    def name(self) -> str: ...

    @property
    def available(self) -> bool: ...

    def speak(self, text: str) -> None: ...


class VoiceInput(Protocol):
    """Something that can listen for one answer.

    Returns the heard text, or ``None`` when input ends (EOF, or a
    scripted source running out of lines).
    """

    @property
    def name(self) -> str: ...

    def listen(self, prompt: str = "") -> str | None: ...


# --- Output backends -------------------------------------------------------

#: System TTS engines, in preference order: (binary, argv builder).
_TTS_ENGINES: tuple[tuple[str, object], ...] = (
    ("espeak-ng", lambda rate, text: ["espeak-ng", "-s", str(rate), text]),
    ("espeak", lambda rate, text: ["espeak", "-s", str(rate), text]),
    ("say", lambda rate, text: ["say", "-r", str(rate), text]),
)


def available_tts_engines() -> list[str]:
    """Names of system TTS engines found on PATH, in preference order."""
    return [name for name, _ in _TTS_ENGINES if shutil.which(name)]


class PrintVoiceOutput:
    """Narrates on screen instead of producing audio.

    Always available; used as the fallback when no system TTS engine
    is installed, and in CI/demo runs where audio is not wanted.
    """

    name = "print"

    @property
    def available(self) -> bool:
        return True

    def speak(self, text: str) -> None:
        print(f"[voice] {text}", file=sys.stdout)


class SystemVoiceOutput:
    """Speaks through the first available system TTS engine."""

    def __init__(self, rate: int = 175) -> None:
        if not 80 <= rate <= 400:
            raise ValueError("rate must be between 80 and 400 words per minute")
        engines = available_tts_engines()
        if not engines:
            raise VoiceError(
                "no system text-to-speech engine found "
                "(install espeak-ng, espeak, or use --voice-output print)"
            )
        self._engine = engines[0]
        self.rate = rate

    @property
    def name(self) -> str:
        return self._engine

    @property
    def available(self) -> bool:
        return True

    def speak(self, text: str) -> None:
        builder = dict(_TTS_ENGINES)[self._engine]
        try:
            subprocess.run(builder(self.rate, text), check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise VoiceError(f"TTS engine {self._engine!r} failed: {exc}") from exc


# --- Input backends --------------------------------------------------------


class ConsoleVoiceInput:
    """Typed fallback for voice input.

    Reads one line from stdin. This is not speech recognition — it is
    the fallback used when no STT engine is available, so a voice-mode
    session still works (questions spoken, answers typed). A real STT
    backend can replace it via the ``VoiceInput`` protocol.
    """

    name = "console"

    def listen(self, prompt: str = "") -> str | None:
        try:
            return input(prompt).strip()
        except EOFError:
            return None


class ScriptedVoiceInput:
    """Feeds canned lines, in order; returns None once exhausted.

    Used by the voice demo and by tests — never for a real session.
    """

    def __init__(self, lines: Sequence[str]) -> None:
        self._lines = list(lines)
        self._index = 0

    @property
    def name(self) -> str:
        return "scripted"

    def listen(self, prompt: str = "") -> str | None:
        if self._index >= len(self._lines):
            return None
        line = self._lines[self._index]
        self._index += 1
        return line.strip()


# --- Configuration / factories ----------------------------------------------


@dataclass(frozen=True)
class VoiceConfig:
    """Voice-mode settings. ``auto`` output prefers system TTS."""

    output: str = "auto"  # auto | system | print
    rate: int = 175  # words per minute for system TTS

    def __post_init__(self) -> None:
        if self.output not in ("auto", "system", "print"):
            raise ValueError("output must be auto, system, or print")
        if not 80 <= self.rate <= 400:
            raise ValueError("rate must be between 80 and 400 words per minute")


def make_voice_output(config: VoiceConfig | None = None) -> VoiceOutput:
    """Build the output backend for a config.

    ``auto`` returns system TTS when an engine is installed, otherwise
    the print fallback. ``system`` raises VoiceError when none is.
    """
    if config is None:
        config = VoiceConfig()
    if config.output == "print":
        return PrintVoiceOutput()
    if config.output == "system":
        return SystemVoiceOutput(rate=config.rate)
    engines = available_tts_engines()
    return SystemVoiceOutput(rate=config.rate) if engines else PrintVoiceOutput()


def describe_voice() -> dict[str, object]:
    """Machine-readable voice capability report (for ``voice --check``)."""
    engines = available_tts_engines()
    return {
        "system_tts_engines": engines,
        "system_tts_available": bool(engines),
        "print_fallback_available": True,
        "speech_recognition_bundled": False,
        "voice_input_fallback": "console (typed)",
    }
