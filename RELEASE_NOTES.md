# v0.5.0 — Native Windows support

Run the bilingual research library on Windows x64 with **Start Web.bat**. The launcher creates a Python 3.12 virtual environment, installs locked dependencies and opens the local web interface. Existing macOS/Linux, PDF-folder, optional Zotero and MCP workflows continue to work.

## Changed

- Native Windows build locking with automatic OS release after process exit.
- Windows-compatible temporary PDF access, reserved filename handling and UTF-8 text/configuration/logs.
- Background task shutdown includes the PDF worker process tree.
- Windows MCP preloads native numerical libraries before starting stdio reads, avoiding a first-search import stall; model weights remain loaded on demand.
- MCP configurations select `.venv\Scripts\python.exe` on Windows; Codex commands use PowerShell quoting, including paths with spaces, Chinese text and apostrophes.
- Windows/Ubuntu portable and native runtime tests, plus a manually triggered fresh Windows installation and real PDF/embedding/web/MCP workflow.
- English and Chinese Windows instructions and updated READMEs.

Native Windows full-pipeline and Windows/Ubuntu runtime checks [passed](https://github.com/FrankPan-30/epilepsy-research-rag/actions/runs/41439404149); existing macOS corpus and MCP regressions also passed.

## Start

Install **Python 3.12 x64**, extract the project ZIP, and double-click **Start Web.bat**. Choose PDFs, download the free local model when prompted, build the index and search. Python remains a prerequisite; this release is not a bundled EXE installer. Windows ARM64 and 32-bit Python are not validated.

See the [Windows guide](https://github.com/FrankPan-30/epilepsy-research-rag/blob/v0.5.0/WINDOWS.md). Windows CI exercises the native runtime on GitHub-hosted Windows Server x64; individual Windows 10/11 desktop and MCP client GUIs have not all been manually tested.

All paper data stays local. No paid AI API or new direct third-party dependency is added.

---

# 中文

新增 Windows x64 原生支持。安装 Python 3.12 64位版本，解压项目，双击 **Start Web.bat**，即可准备环境并打开中英双语网页，导入 PDF、检索和查看原文引用。

本次适配覆盖文件锁、临时 PDF 访问、中文路径/编码、后台进程退出和 MCP 配置生成。已有 macOS、Linux、Zotero 和 Codex/MCP 用法保留。Windows/Ubuntu 原生测试与全新 Windows 依赖安装、真实文献流程纳入验证。

仍需安装 Python；独立 EXE 安装包与 ARM64/32位版本尚未提供或验证。Windows 自动测试运行在 Windows Server x64，普通 Windows 桌面与各 MCP 客户端 GUI 尚未逐一手测。详见 [Windows 使用指南](https://github.com/FrankPan-30/epilepsy-research-rag/blob/v0.5.0/WINDOWS.md)。
