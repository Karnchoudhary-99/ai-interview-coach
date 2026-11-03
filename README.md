# AI Interview Coach

Mock interviews with LLM feedback, voice + text — practice interviews with
structured questions, answer scoring, and actionable feedback.

## Roadmap

- [x] Project scaffold (README roadmap, license, gitignore)
- [x] Question bank + interview session engine
- [x] Answer scoring + feedback reports
- [ ] Voice input/output support
- [ ] Self-review checklist, then public

## Question bank + session engine

A bundled bank of 30 questions across 5 categories (behavioral,
algorithms, system design, Python, databases) and 3 difficulty levels,
each with ideal answer points and follow-ups. Sessions are seeded and
reproducible, support skipping, per-question timing, and JSON
transcripts.

```bash
# List questions, optionally filtered
PYTHONPATH=src python -m interview_coach bank --category python --difficulty junior

# Run an interactive mock interview (5 questions, transcript to JSON)
PYTHONPATH=src python -m interview_coach practice --count 5 --seed 42 \
  --transcript transcript.json

# Scripted, non-interactive demo
PYTHONPATH=src python examples/demo.py
```

Custom banks are plain JSON lists of question objects
(`id`, `text`, `category`, `difficulty`, `ideal_points`, `follow_ups`,
`time_limit_seconds`); pass one with `--bank path/to/bank.json`.

## Answer scoring + feedback reports

Scoring is offline and deterministic: an ideal point counts as covered
when at least 60% of its content words (framing verbs like "shows" and
"describes" excluded) are evidenced in the answer, with light stemming
and noun/verb prefix matching so "listened" evidences "listening".
Skipped and unreached questions score 0. Bands: 80+ strong, 50+
developing, below 50 needs work. Reports give per-category scores,
strengths and focus areas, per-question covered/missed points, and a
concrete next step per missed point — and state their own limit:
coverage is not a judgement of correctness, tone, or structure.

```bash
# Score a saved transcript, print the text report, save Markdown too
PYTHONPATH=src python -m interview_coach score --transcript transcript.json \
  --report report.md

# Get the report straight after a practice session
PYTHONPATH=src python -m interview_coach practice --count 5 --seed 42 \
  --transcript transcript.json --report report.md
```

## License

MIT — see [LICENSE](LICENSE).
