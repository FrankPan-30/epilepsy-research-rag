# v0.4.0 — Bilingual local web interface

Import PDFs, search papers and inspect original citations in a local browser. The new Chinese/English interface works alongside the existing CLI, optional Zotero import and stdio MCP integrations.

## New

- macOS double-click launcher (`Start Web.command`) and Linux shell launcher, with missing-dependency installation.
- Batch PDF selection, folder selection and PDF drag-and-drop, exact-file deduplication and explicit local-model download.
- Background indexing with progress and diagnostics; separate web-import workspace that preserves the main library and settings.
- Hybrid/keyword search, full library catalog, PDF-page viewer, page navigation, citation copying and original-PDF download.
- Chinese/English controls, result labels, common error messages and remembered language preference. Paper content stays in its original language.
- Loopback-only server, session/origin checks, validated uploads, and index-version/PDF-hash checks for citations.
- English and Chinese instructions and screenshots using a synthetic document.

## Start

With Python 3.12 installed on macOS, double-click **Start Web.command**. Choose PDFs, download the free local model if prompted, build the index and search. Existing installations reuse dependencies and model weights. Details: [Web UI guide](https://github.com/FrankPan-30/epilepsy-research-rag/blob/v0.4.0/WEB_UI.md).

## Validation and scope

- 29 portable tests: existing configuration/import tests plus 11 HTTP tests.
- Two complete integration tests with generated PDFs: existing CLI/MCP flow and new web upload/build/search/source flow.
- Original-library regression: 28 tests, 8 anchored retrieval cases in each retrieval mode and 9 MCP tools.
- Actual browser checks: upload, build, Chinese/English queries and language switching, page navigation and citation copying; narrow and desktop layouts inspected.

Web copies and indices stay under ignored `data/web/`. Existing CLI/Zotero/MCP settings are preserved. The web interface uses no paid API, and retrieves evidence rather than generating answers. It is a local single-user application, not a hosted chat or remote MCP service. Python 3.12 is required; native Windows and a signed desktop installer are not included.

---

# 中文

新增中英双语本地网页：导入 PDF/文件夹、建立独立文库、检索、查看与翻阅原文、复制页码引用和下载原件。macOS 安装 Python 3.12 后双击 **Start Web.command**；原有 Zotero、命令行和 MCP 用法继续保留。

网页数据留在本机 `data/web/`，不随代码上传；没有新增付费 API。操作按钮、结果标签和常见错误提示支持中英切换，论文与原始技术日志保留原语言。网页负责证据检索与核查，生成式分析继续通过 MCP 客户端完成。详见 [双语网页指南](https://github.com/FrankPan-30/epilepsy-research-rag/blob/v0.4.0/WEB_UI.md)。
