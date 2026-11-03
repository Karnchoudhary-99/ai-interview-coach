"""Voice-mode demo without a microphone: scripted answers, printed speech.

Run: PYTHONPATH=src python examples/voice_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from interview_coach.bank import load_bank
from interview_coach.report import render_text, score_session
from interview_coach.session import InterviewSession, SessionConfig
from interview_coach.voice import PrintVoiceOutput, ScriptedVoiceInput

ANSWERS = [
    "I led a migration where requirements changed weekly. I created clarity "
    "with a short decision log, kept stakeholder communication weekly, and "
    "made explicit trade-offs under uncertainty about scope versus schedule.",
    "skip",
]


def main() -> int:
    output = PrintVoiceOutput()
    voice_input = ScriptedVoiceInput(ANSWERS)
    session = InterviewSession(load_bank(), SessionConfig(2, seed=5))
    question = session.start()
    while question is not None:
        output.speak(question.text)
        heard = voice_input.listen()
        if heard is None or heard.lower() == "skip":
            question = session.skip()
        else:
            question = session.answer(heard)
    result = session.result()
    output.speak(f"Done: {len(result.answered)} answered, {len(result.skipped)} skipped.")
    print()
    print(render_text(score_session(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
