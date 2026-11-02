@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0" || exit /b 1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if exist ".venv\Scripts\python.exe" goto environment_ready
py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 goto try_python
py -3.12 -m venv .venv
if errorlevel 1 goto failed
goto environment_ready
:try_python
python -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 goto need_python
python -m venv .venv
if errorlevel 1 goto failed
:environment_ready
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 goto need_python
".venv\Scripts\python.exe" -c "import importlib.metadata as m; [m.version(x) for x in ('PyMuPDF','pymupdf4llm','sentence-transformers','rapidocr-onnxruntime','mcp')]" >nul 2>&1
if not errorlevel 1 goto launch
echo First launch: installing dependencies. No paid API is used.
echo 首次启动：正在安装依赖，不调用付费 API。
".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
if errorlevel 1 goto failed
:launch
".venv\Scripts\python.exe" web_app.py %*
if errorlevel 1 goto failed
popd
exit /b 0
:need_python
echo Install Python 3.12 ^(64-bit, x86-64^) from https://www.python.org/downloads/windows/
echo Enable the Python launcher or Add python.exe to PATH, then double-click again.
echo 请先安装 Python 3.12 64位版本，并安装 py 启动器或勾选加入 PATH，然后重新双击。
echo An existing incompatible .venv must be moved aside before recreating the environment.
:failed
echo Startup failed. Read the message above. / 启动失败，请查看上方提示。
if not defined RAG_LAUNCHER_NO_PAUSE pause
popd
exit /b 1
