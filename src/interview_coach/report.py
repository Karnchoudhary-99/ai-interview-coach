"""Feedback reports: turn a SessionScore into actionable advice.

A report answers three questions: how did I do overall, where am I
strong or weak, and what exactly should I add next time? Missed ideal
points are quoted verbatim — the candidate's next practice round has a
concrete checklist, not a vague "be more specific". The report is
honest about its limits: scoring is word-coverage against the bank's
ideal points, not a judgement of correctness, tone, or structure, and
it says so in its own footer.
"""

from __future__ import annotations

from .models import SessionResult
from .scoring import SessionScore, score_session

_LIMIT_NOTE = (
    "Scoring is word-coverage against each question's ideal points, "
    "not a judgement of correctness, tone, or structure. A point can be "
    "covered by mentioning its words without a good argument, and a good "
    "answer can miss a point by paraphrasing it beyond recognition."
)


def build_report(result: SessionResult) -> SessionScore:
    """Score a session transcript (alias that reads as a report step)."""
    return score_session(result)


def strengths_and_gaps(score: SessionScore) -> tuple[list[str], list[str]]:
    """Strong (>=80) and weak (<50) categories, strongest/weakest first."""
    category_scores = score.category_scores()
    strengths = sorted(
        (cat for cat, value in category_scores.items() if value >= 80),
        key=lambda cat: -category_scores[cat],
    )
    gaps = sorted(
        (cat for cat, value in category_scores.items() if value < 50),
        key=lambda cat: category_scores[cat],
    )
    return strengths, gaps


def action_items(score: SessionScore) -> list[str]:
    """One concrete next step per missed point, weakest questions first."""
    items: list[str] = []
    for item in sorted(score.per_question, key=lambda q: q.score):
        if item.skipped:
            items.append(f"Answer {item.question.id} instead of skipping it ({item.question.text})")
        elif item.answer is None:
            items.append(f"Reach {item.question.id} — it was never answered ({item.question.text})")
        else:
            for point in item.missed_points:
                items.append(f"On {item.question.id}, cover: {point}")
    return items


def render_text(score: SessionScore) -> str:
    """Plain-text report for the terminal."""
    strengths, gaps = strengths_and_gaps(score)
    lines = [
        f"Interview feedback — overall {score.overall:.0f}/100 ({score.band})",
        (
            f"Answered: {len(score.per_question) - score.skipped_count - score.unanswered_count}"
            f", skipped: {score.skipped_count}, unreached: {score.unanswered_count}"
            f", over time limit: {score.over_time_count}, total {score.total_seconds:.0f}s."
        ),
        "",
    ]
    if score.category_scores():
        lines.append("By category:")
        for category, value in score.category_scores().items():
            lines.append(f"  {category}: {value:.0f}/100")
        lines.append("")
    if strengths:
        lines.append(f"Strengths: {', '.join(strengths)}.")
    if gaps:
        lines.append(f"Focus areas: {', '.join(gaps)}.")
    if strengths or gaps:
        lines.append("")
    lines.append("Per question:")
    for item in score.per_question:
        status = "skipped" if item.skipped else "unreached" if item.answer is None else f"{item.score:.0f}/100"
        overtime = " (over time limit)" if item.over_time_limit else ""
        lines.append(f"  {item.question.id} [{item.question.category}]: {status}{overtime}")
        for point in item.missed_points:
            lines.append(f"    missed: {point}")
    lines.append("")
    lines.append("Next steps:")
    for item in action_items(score)[:10]:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append(_LIMIT_NOTE)
    return "\n".join(lines)


def render_markdown(score: SessionScore) -> str:
    """Markdown report, suitable for saving alongside a transcript."""
    strengths, gaps = strengths_and_gaps(score)
    lines = [
        "# Interview feedback",
        "",
        (
            f"**Overall: {score.overall:.0f}/100 ({score.band})** — "
            f"answered {len(score.per_question) - score.skipped_count - score.unanswered_count}, "
            f"skipped {score.skipped_count}, unreached {score.unanswered_count}, "
            f"over time limit {score.over_time_count}, total {score.total_seconds:.0f}s."
        ),
        "",
        "## By category",
        "",
    ]
    for category, value in score.category_scores().items():
        lines.append(f"- {category}: {value:.0f}/100")
    lines.append("")
    if strengths:
        lines.append(f"**Strengths:** {', '.join(strengths)}.")
        lines.append("")
    if gaps:
        lines.append(f"**Focus areas:** {', '.join(gaps)}.")
        lines.append("")
    lines.append("## Per question")
    lines.append("")
    for item in score.per_question:
        status = "skipped" if item.skipped else "unreached" if item.answer is None else f"{item.score:.0f}/100"
        overtime = " (over time limit)" if item.over_time_limit else ""
        lines.append(f"- **{item.question.id}** [{item.question.category}] — {status}{overtime}")
        for point in item.covered_points:
            lines.append(f"  - covered: {point}")
        for point in item.missed_points:
            lines.append(f"  - missed: {point}")
    lines.append("")
    lines.append("## Next steps")
    lines.append("")
    for item in action_items(score)[:10]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append(f"> {_LIMIT_NOTE}")
    return "\n".join(lines)


def load_transcript(path: str) -> SessionResult:
    """Rebuild a SessionResult from a transcript JSON file (see CLI score)."""
    import json
    from pathlib import Path

    from .models import Answer, Question

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"transcript file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"transcript file is not valid JSON: {path} ({exc})") from None
    try:
        questions = [Question.from_dict(entry) for entry in raw["questions"]]
        answers = [
            Answer(
                question_id=str(entry["question_id"]),
                text=str(entry["text"]),
                elapsed_seconds=float(entry["elapsed_seconds"]),
                skipped=bool(entry.get("skipped", False)),
            )
            for entry in raw["answers"]
        ]
        total = float(raw.get("total_seconds", 0.0))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"transcript file has an unexpected shape: {exc}") from None
    return SessionResult(questions=questions, answers=answers, total_seconds=total)
