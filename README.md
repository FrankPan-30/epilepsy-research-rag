# Epilepsy Research RAG

**Search your Zotero papers in English or Chinese, inspect page-level evidence, and compare seizure-prediction methods with Codex.**

[![Portable checks](https://github.com/FrankPan-30/epilepsy-research-rag/actions/workflows/tests.yml/badge.svg)](https://github.com/FrankPan-30/epilepsy-research-rag/actions/workflows/tests.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)

**English** | [简体中文](README.zh-CN.md)

A local literature-retrieval toolkit built around a real epilepsy-prediction research workflow. It keeps your Zotero PDFs, parsed text and retrieval index on your computer, then exposes evidence to Codex through nine read-only MCP tools. Codex performs the synthesis in your chat; retrieved passages sent to it are processed by the cloud model.

> “Compare alarm postprocessing across cross-patient studies. Show the validation protocol, smoothing and threshold rules, false-alarm definition, and original PDF pages.”

## Try it without a Zotero library

With Python 3.12 on macOS or Linux:

```bash
git clone https://github.com/FrankPan-30/epilepsy-research-rag.git
cd epilepsy-research-rag
python3 demo.py
python3 demo.py 'LOPOCV validation'
```

No package installation, model download or API key is required for this demo. It runs the real keyword-search path against three **synthetic notes**, in a temporary index that is automatically removed. Example output:

```text
SYNTHETIC DEMO | keyword retrieval | no model download | no API call
Question: 误报后处理中的平滑和阈值

1. Synthetic note: alarm postprocessing [DEMO-ALARM]
Record false alarm rate together with threshold, smoothing, consecutive confirmation, and refractory period. Compare alarm settings under the same evaluation protocol.
```

The demo illustrates retrieval mechanics. Real-paper search, embeddings, PDF extraction and MCP require the full setup below.

## What it does

| Research need | Implemented support |
|---|---|
| Find methods across languages | SQLite FTS5 keyword search, Chinese-to-English domain expansion, local multilingual E5 embeddings and reciprocal rank fusion |
| Check an answer against its source | Zotero item/attachment keys, PDF page numbers, source passages, adjacent pages and PDF-page images |
| Compare evaluation protocols | Candidate evidence maps for validation, prediction horizons, alarm postprocessing, metrics and limitations |
| Keep evidence types distinct | Separate full text, OCR, metadata-only entries, user notes and project guidance; paper search excludes personal notes by default |
| Update a growing collection | Manual incremental sync, PDF hashes, cached parsing/embeddings and atomic index generation switches |
| Record research decisions | Versioned experiment records, separate window/event metrics, and five research workflow guides |

The domain workflow pays particular attention to **within-patient leave-one-seizure-out versus cross-patient leave-one-patient-out**, and to **window metrics versus event sensitivity, FA/h and alarm rules**. Terminology and definitions still need checking in each source paper.

## How it works

```mermaid
flowchart LR
    A[Local Zotero collection] --> B[PDF parsing and selective OCR]
    B --> C[Page-aware chunks and source metadata]
    C --> D[Local SQLite FTS5 and E5 vectors]
    D --> E[Hybrid retrieval]
    E --> F[CLI or read-only MCP tools]
    F --> G[Codex cloud synthesis]
    G --> H[Check citations and original PDF pages]
```

Defaults: `intfloat/multilingual-e5-small`, 420-token chunks, 45-token overlap, 40 candidates per retrieval route, eight returned chunks and at most three chunks per paper. RRF combines rankings; it is not a neural reranker. Ranking scores are not confidence estimates.

## Use your own Zotero collection

The complete pipeline has been exercised on **macOS Apple Silicon with Python 3.12**. Portable CI checks run on Ubuntu. Native Windows is not supported yet because the build lock uses `fcntl`; the full pipeline has not been validated on every Linux environment.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python configure.py --zotero-dir "$HOME/Zotero" --collection-name 'Epilepsy Prediction'
.venv/bin/python download_model.py
.venv/bin/python rag.py sync
.venv/bin/python rag.py status
```

Replace `Epilepsy Prediction` with your own Zotero collection name. The collection and its descendants are included. Use `--collection-key YOUR_KEY` if names are ambiguous. Configuration is written to ignored `config.json`; initialization preserves an existing file. The default collection name in the template is `癫痫预测`.

The reader takes a read-only SQLite snapshot of the local Zotero database and never writes to Zotero. Stored PDF attachments are supported. Zotero `attachments:` linked-base paths are not currently resolved. Dependencies and the pinned public embedding model need an initial download; parsing, embedding and retrieval then run locally without a paid API.

### Connect to Codex

```bash
.venv/bin/python configure.py --print-mcp
```

Run the printed `codex mcp add` command. It uses the absolute path of your clone. Review an existing connection with the same name before replacing it. The project does not automatically edit your global Codex settings.

Ask Codex to use `epilepsy_research`, for example:

> Search my epilepsy research library for alarm postprocessing in cross-patient studies. Compare protocols and cite original PDF pages. Separate paper evidence from proposed experiments.

### Use the CLI

```bash
.venv/bin/python rag.py search 'false alarm smoothing threshold' --limit 8
.venv/bin/python rag.py search '跨患者预测中的误报和报警后处理' --limit 8
.venv/bin/python rag.py paper ZOTERO_ITEM_KEY
.venv/bin/python rag.py read CHUNK_ID --neighbors 1
.venv/bin/python rag.py catalog --field alarm_postprocessing
```

Use actual keys and chunk IDs from your results. Keep the returned generation identifier with citations; rerun a search after rebuilding before reusing chunk IDs.

For a systematic comparison, enumerate the catalog and record per-paper coverage. Ranked top-k search alone does not establish that every relevant paper has been reviewed.

### Update code and papers

```bash
git pull --ff-only
.venv/bin/python rag.py sync
```

Resolve your own uncommitted code changes before pulling. `sync` reuses unchanged parsing and vectors, builds a separate generation, and switches the active index only on success. Old generations remain available until you explicitly clean them up. Code updates and local library updates are separate operations.

See the [Chinese maintenance guide](UPDATING.md) for push, migration and recovery steps. Experiment records are created explicitly with `experiments.py`; templates are plans, not completed results.

## Evidence boundaries and validation

- Field maps locate keyword-matched passages. They are **candidates for source checking**, not verified study classifications or normalized results.
- PDF text, formulas and table layout can be imperfect. Selective local OCR saves its own provenance; inspect the PDF image for table columns, equations and model diagrams.
- Metadata-only records are labeled. Local method-review notes describe the specific checked claims and PDF hashes, rather than certifying an entire paper.
- The original development corpus contains 125 bibliographic items, 76 PDFs, 1,077 pages and 4,982 chunks. **These private documents and their index are not distributed.**
- On eight source-anchored development queries, both keyword-only and hybrid retrieval found the target paper within 12 returned chunks: **8/8 for each**. This small tuning set does not measure generated-answer accuracy or demonstrate a hybrid-search advantage. A further 22 review questions are provided but not scored.

This is a research literature tool, not a seizure prediction model or a clinical decision system.

Run the public checks:

```bash
python3 demo.py --check
# PyMuPDF is the only external dependency needed for these unit tests.
python3 -m pip install pymupdf==1.26.7
python3 -m unittest tests.UnitTests -v
```

With a complete local environment and corpus, run `.venv/bin/python validate.py`. The original corpus tests and `evaluation_cases.json` contain corpus-specific keys; adapt them for your own collection. See [BUILD_REPORT.md](BUILD_REPORT.md) for the original validation record. Full dependency installation on a fresh machine is separate from the small public CI checks.

## Data, costs and licensing

PDFs, `data/`, `models/`, `.venv/`, personal configuration and credentials are excluded from Git. Original PDFs stay in Zotero. Keep private notes and unpublished results out of public issues and pull requests.

The toolkit makes no paid embedding, OCR or generation API calls. Codex usage follows your own account arrangement. The included CI uses a standard runner on this public repository, with no model download, paid AI API, or artifact/cache storage.

Project source and original synthetic examples are licensed under **[GNU AGPL v3.0](LICENSE)**. Copyright © 2026 FrankPan-30 and contributors. See [third-party components](THIRD_PARTY.md), including the AGPL PDF stack. Papers and user-supplied data retain their own rights.

## Contribute

Useful contributions include English workflow translations, redistributable retrieval fixtures, held-out evaluation cases, and Linux installation reports. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [roadmap](ROADMAP.md).

- [Report a bug or suggest a feature](https://github.com/FrankPan-30/epilepsy-research-rag/issues/new/choose)
- [Discuss research workflows](https://github.com/FrankPan-30/epilepsy-research-rag/discussions)

If this helps your research, a star makes the project easier for other researchers to discover. Feedback on a real workflow is especially welcome.

Built with [Zotero](https://www.zotero.org/), [PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM), [multilingual E5](https://huggingface.co/intfloat/multilingual-e5-small), [Sentence Transformers](https://github.com/huggingface/sentence-transformers), [RapidOCR](https://github.com/RapidAI/RapidOCR) and the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
