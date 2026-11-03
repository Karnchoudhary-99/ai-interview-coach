"""Command-line interface for the interview coach."""

from __future__ import annotations

import argparse
import json
import sys

from .bank import categories, filter_bank, load_bank
from .models import Difficulty
from .session import InterviewSession, SessionConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="interview-coach", description="Mock interviews with structured feedback.")
    sub = parser.add_subparsers(dest="command", required=True)

    bank_parser = sub.add_parser("bank", help="List questions in the bank")
    bank_parser.add_argument("--category", default=None, help="Filter by category")
    bank_parser.add_argument("--difficulty", default=None, choices=[d.value for d in Difficulty])
    bank_parser.add_argument("--bank", default=None, help="Path to a custom question-bank JSON file")

    practice = sub.add_parser("practice", help="Run an interactive mock interview")
    practice.add_argument("--count", type=int, default=5, help="Number of questions (default 5)")
    practice.add_argument("--category", default=None, help="Limit questions to a category")
    practice.add_argument("--seed", type=int, default=None, help="Seed for reproducible selection")
    practice.add_argument("--bank", default=None, help="Path to a custom question-bank JSON file")
    practice.add_argument("--transcript", default=None, help="Write the session transcript as JSON here")
    return parser


def _cmd_bank(args: argparse.Namespace) -> int:
    questions = filter_bank(load_bank(args.bank), category=args.category, difficulty=args.difficulty)
    if not questions:
        print("No questions match those filters.")
        print(f"Categories: {', '.join(categories(load_bank(args.bank)))}")
        return 0
    for question in questions:
        print(f"[{question.id}] ({question.category}/{question.difficulty.value}) {question.text}")
    return 0


def _cmd_practice(args: argparse.Namespace) -> int:
    session = InterviewSession(load_bank(args.bank), SessionConfig(args.count, args.category, args.seed))
    question = session.start()
    print(f"Mock interview started: {session.position[1]} questions. Type 'skip' to pass.\n")
    while question is not None:
        pos, total = session.position
        print(f"Q{pos}/{total} [{question.category}/{question.difficulty.value}]: {question.text}")
        for follow_up in question.follow_ups:
            print(f"  (follow-up: {follow_up})")
        try:
            text = input("Your answer: ").strip()
        except EOFError:
            print("\nInput ended; finishing early.")
            break
        if text.lower() == "skip":
            question = session.skip()
        else:
            question = session.answer(text) if text else session.skip()
        print()
    result = session.result()
    print(
        f"Done: {len(result.answered)} answered, {len(result.skipped)} skipped, "
        f"{result.total_seconds:.0f}s total."
    )
    if args.transcript:
        with open(args.transcript, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2)
        print(f"Transcript written to {args.transcript}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "bank":
        return _cmd_bank(args)
    return _cmd_practice(args)


if __name__ == "__main__":
    sys.exit(main())
