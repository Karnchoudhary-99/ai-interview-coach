# AI Interview Coach

Mock interviews with LLM feedback, voice + text — practice interviews with
structured questions, answer scoring, and actionable feedback.

## Roadmap

- [x] Project scaffold (README roadmap, license, gitignore)
- [x] Question bank + interview session engine
- [ ] Answer scoring + feedback reports
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
`time_limit_seconds`); pass one with `--bank path/to/bank.json`. The
scoring engine in the next chunk grades answers against each
question's `ideal_points`.

## License

MIT — see [LICENSE](LICENSE).
