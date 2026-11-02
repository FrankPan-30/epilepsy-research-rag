# v0.3.0 — PDF folders and more MCP clients

Build a research library directly from a folder of PDFs. Zotero is now an optional import source; existing Zotero configurations, item keys and Codex registrations keep working.

## New

- Recursive PDF import, SHA256-based identity and exact-file deduplication.
- Optional `paper.pdf.json` bibliographic metadata with field provenance and conflict checking.
- Source-appropriate file/page citations, retaining Zotero links for Zotero records.
- Configuration generation and instructions for Claude Desktop, Cursor and VS Code's compatibility format, alongside the existing Codex command.
- English and Chinese quick starts that begin with ordinary PDFs.

## Try it

After installing dependencies, initialize a fresh clone with:

```bash
.venv/bin/python configure.py --pdf-dir '/absolute/path/to/My Papers'
.venv/bin/python download_model.py
.venv/bin/python rag.py sync
```

Choose your MCP client, or use CLI search directly. Existing installations do not need to rerun initialization. `configure.py` protects their current settings.

## Validation and scope

Portable tests cover PDF import, metadata, duplicate handling, source-specific links and generated client configurations. A separate integration test generates PDFs in a disposable clone and runs real parsing, local embeddings, search, incremental updates and MCP page/image retrieval without Zotero.

The server's stdio protocol is tested through the MCP SDK. Other desktop-client interfaces are documented from official configuration references and have not each been manually exercised. This release supplies local stdio, not an HTTP service or standalone chat UI.

One clone maintains one active source/index. Identical PDF bytes share an ID; changing the bytes creates a new ID. Empty or invalid folder configurations keep the previous index active. Original PDFs, sidecars, indices, model weights and personal client settings stay outside Git.
