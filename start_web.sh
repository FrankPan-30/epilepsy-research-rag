#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  if command -v python3.12 >/dev/null 2>&1; then RAG_PYTHON=python3.12; else RAG_PYTHON=python3; fi
  if ! "$RAG_PYTHON" -c 'import sys; assert sys.version_info[:2] == (3,12)' 2>/dev/null; then
    echo 'Please install Python 3.12 from python.org, then double-click again.'
    echo '请先从 python.org 安装 Python 3.12，再双击启动。'
    read -r -p 'Press Enter / 按回车退出 ' _
    exit 1
  fi
  "$RAG_PYTHON" -m venv .venv
fi
if ! .venv/bin/python -c 'import importlib.metadata as m; [m.version(x) for x in ("PyMuPDF", "pymupdf4llm", "sentence-transformers", "rapidocr-onnxruntime", "mcp")]' >/dev/null 2>&1; then
  echo 'First launch: installing dependencies. No paid API is used.'
  echo '首次启动：正在安装依赖，不调用付费 API。'
  .venv/bin/python -m pip install -r requirements.lock.txt
fi
.venv/bin/python web_app.py "$@"
