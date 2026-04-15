# Contributing

Thank you for your interest in contributing to photo-ai-workflow.

## Getting started

```bash
git clone https://github.com/<your-fork>/photo-ai-workflow.git
cd photo-ai-workflow
python -m pip install -e ".[dev]"
```

## Running tests

```bash
python -m pytest -q tests/
```

All tests must pass before opening a pull request.

## Pull request checklist

- [ ] Tests added or updated for your change
- [ ] `python -m pytest -q tests/` passes locally
- [ ] No absolute local paths left in code or docs
- [ ] `.env` is not committed (add secrets to `.env.example` as placeholders only)

## Reporting issues

Open a GitHub Issue with:
1. Your OS and Python version
2. The exact command you ran
3. The full error output

## Code style

Plain `black`-compatible indentation (4 spaces). No strict linter enforced yet — just keep it readable.
