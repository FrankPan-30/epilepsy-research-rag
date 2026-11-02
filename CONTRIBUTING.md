# Contributing

Thanks for helping make literature evidence easier to inspect.

## Start small

Run the dependency-free demo with Python 3.12:

```bash
python3 demo.py --check
```

Install the project dependencies in a virtual environment for development. Run the portable tests with `.venv/bin/python -m unittest tests.UnitTests -v`. Full-corpus checks require a local Zotero library and the model; see README.

Useful contributions are listed in [ROADMAP.md](ROADMAP.md). Before a large change, describe the problem and proposed behavior in an issue. Small fixes can go straight to a pull request.

## Evidence and reproducibility

- Use synthetic or openly licensed fixtures that you may redistribute.
- Keep private PDFs, patient data, database exports, credentials and local configuration out of issues and PRs.
- Record the parser/model version and a minimal reproduction for retrieval or extraction failures.
- Separate a retrieval metric from generated-answer correctness. Explain test-set construction and whether cases were used for tuning.
- Keep window metrics, event metrics, and evaluation protocols separate.
- Mark automatic extraction, OCR, and unchecked hypotheses clearly.

## Pull requests

Use a focused branch (for example `codex/fix-query-tokenization`), describe the problem and resulting behavior, and include relevant validation. Do not change the user's library or generate an index as an import side effect. Preserve offline retrieval and explicit cloud-cost boundaries.

Contributions are provided under this project's AGPL-3.0 license. Third-party material retains its own license and attribution.
