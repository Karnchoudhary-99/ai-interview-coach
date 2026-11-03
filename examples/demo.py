"""Scripted demo: runs a 3-question mock interview without interaction.

Usage: PYTHONPATH=src python examples/demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from interview_coach.bank import load_bank
from interview_coach.session import InterviewSession, SessionConfig

CANNED_ANSWERS = [
    "I disagreed with a teammate about moving to microservices. I listened to their "
    "scaling concerns, proposed a trial on one service, and we agreed on that compromise.",
    "A hash map from value to index gives O(n) time: one pass to build it, one pass to look up.",
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


if __name__ == "__main__":
    main()
