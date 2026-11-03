"""Scripted demo: runs a 3-question mock interview without interaction.

Usage: PYTHONPATH=src python examples/demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from interview_coach.bank import load_bank
from interview_coach.report import render_text, score_session
from interview_coach.session import InterviewSession, SessionConfig

# Scripted answers matched to the seed-42 selection (py-02, sys-03, alg-05),
# so the demo's feedback report shows real coverage instead of a 0/100
# caused by answering different questions than the ones asked.
CANNED_ANSWERS = [
    "Generators use lazy evaluation, yielding one item at a time, so their memory "
    "profile stays flat on large streams, unlike lists. The trade-off is the "
    "single-pass limitation: once consumed, a generator cannot be rewound.",
    "Use queue-based fan-out per channel, retry with backoff and dead-letter "
    "handling for failures, and idempotency for at-least-once delivery so "
    "duplicate deliveries are safe.",
    "skip",
]


def main() -> None:
    session = InterviewSession(load_bank(), SessionConfig(question_count=3, seed=42))
    question = session.start()
    for canned in CANNED_ANSWERS:
        if question is None:
            break
        pos, total = session.position
        print(f"Q{pos}/{total} [{question.id}]: {question.text}")
        if canned == "skip":
            print("  -> skipped")
            question = session.skip()
        else:
            print(f"  -> {canned}")
            question = session.answer(canned)
    result = session.result()
    print(f"\nAnswered: {len(result.answered)}, skipped: {len(result.skipped)}")
    print(json.dumps(result.to_dict(), indent=2))
    print()
    print(render_text(score_session(result)))


if __name__ == "__main__":
    main()
