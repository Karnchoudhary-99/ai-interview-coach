"""Command-line interface for the interview coach."""

from __future__ import annotations

import argparse
import json
import sys

from .bank import categories, filter_bank, load_bank
from .models import Difficulty
from .report import load_transcript, render_markdown, render_text, score_session
from .session import InterviewSession, SessionConfig
from .voice import (
    ConsoleVoiceInput,
    VoiceConfig,
    VoiceError,
    describe_voice,
    make_voice_output,
)


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
    practice.add_argument("--report", default=None, help="Write the feedback report as Markdown here")

    score = sub.add_parser("score", help="Score a saved session transcript")
    score.add_argument("--transcript", required=True, help="Transcript JSON file to score")
    score.add_argument("--report", default=None, help="Write the feedback report as Markdown here")
    score.add_argument("--json", default=None, help="Write the machine-readable score as JSON here")

    voice = sub.add_parser("voice", help="Check voice backends, speak text, or listen once")
    voice.add_argument("--check", action="store_true", help="Report available voice backends")
    voice.add_argument("--say", default=None, help="Speak this text (system TTS or print fallback)")
    voice.add_argument("--listen", action="store_true", help="Listen for one answer (typed fallback)")
    voice.add_argument(
        "--voice-output", default="auto", choices=["auto", "system", "print"],
        help="Voice output backend (default auto)",
    )
    voice.add_argument("--rate", type=int, default=175, help="System TTS rate in wpm (default 175)")
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


def _write_report(score, path: str | None) -> None:
    """Print the text report and, when requested, save the Markdown one."""
    print()
    print(render_text(score))
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(score))
        print(f"Report written to {path}")


def _cmd_voice(args: argparse.Namespace) -> int:
    try:
        config = VoiceConfig(output=args.voice_output, rate=args.rate)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.check or (not args.say and not args.listen):
        info = describe_voice()
        print(f"System TTS engines: {', '.join(info['system_tts_engines']) or 'none found'}")
        print(f"Print fallback: {'available' if info['print_fallback_available'] else 'unavailable'}")
        print("Speech recognition bundled: no (voice input falls back to typed lines)")
        print(f"Voice input fallback: {info['voice_input_fallback']}")
        return 0
    if args.say:
        try:
            make_voice_output(config).speak(args.say)
        except VoiceError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0
    heard = ConsoleVoiceInput().listen("Say your answer (typed fallback): ")
    if heard is None:
        print("No input received.")
    else:
        print(f"Heard: {heard}")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    try:
        result = load_transcript(args.transcript)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    scored = score_session(result)
    _write_report(scored, args.report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(scored.to_dict(), fh, indent=2)
        print(f"Score written to {args.json}")
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
    if args.report:
        _write_report(score_session(result), args.report)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "bank":
        return _cmd_bank(args)
    if args.command == "score":
        return _cmd_score(args)
    if args.command == "voice":
        return _cmd_voice(args)
    return _cmd_practice(args)


if __name__ == "__main__":
    sys.exit(main())
