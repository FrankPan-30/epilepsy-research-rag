# v0.2.0 — First public release

Epilepsy Research RAG helps researchers search a local Zotero collection and compare seizure-prediction methods with source passages and original PDF pages.

## Start here

Run `python3 demo.py` after cloning to try a synthetic keyword-search example with no dependencies, model download or API key. Follow the README to connect your own Zotero collection and Codex.

## Included

- Local PDF parsing and selective OCR; SQLite FTS5 + multilingual E5 hybrid retrieval.
- Page-level provenance, source-type separation, candidate method/evaluation evidence maps and nine read-only MCP tools.
- Incremental indexing, research workflow guides and versioned local experiment records.
- English and Chinese guides, AGPL-3.0 licensing, contributor templates and portable GitHub Actions checks.

## Scope

The complete pipeline has been exercised on macOS Apple Silicon / Python 3.12. Portable checks cover the synthetic demo and unit tests; they do not validate every PDF parser or every operating system. Native Windows is not supported yet.

Private papers, indices, model weights and experiment records are excluded. Field maps need source checking. The eight-query development check is a retrieval smoke test, not an answer-quality benchmark.

Feedback on real research workflows, English guide translations, redistributable test fixtures and Linux setup is welcome through Issues, Discussions and pull requests.
