# Windows setup / Windows 使用指南

## 中文

适配目标是 **Windows 10/11 x64 + Python 3.12 64位（x86-64）**。网页功能与 macOS 相同，中英文界面、PDF/文件夹导入、检索和原文引用均可使用。无需 WSL、Zotero、Codex 或 API key。

1. 从 [Python 官方网站](https://www.python.org/downloads/windows/)安装 Python **3.12** 的 64位版本。保留 `py` 启动器，或勾选 **Add python.exe to PATH**。[官方安装说明](https://docs.python.org/3.12/using/windows.html)。
2. [下载项目 ZIP](https://github.com/FrankPan-30/epilepsy-research-rag/archive/refs/heads/main.zip)，先解压到可写的本地文件夹，再双击 **Start Web.bat**。选择较短的路径，例如用户目录下的 `ResearchRAG`，可减少旧式 Windows 路径长度限制的影响。
3. 首次会创建 `.venv` 并安装锁定依赖。安装期间保持窗口打开；失败时窗口保留提示，修正网络或环境问题后再次双击。
4. 浏览器打开后，选择 PDF/文件夹。首次按提示下载免费本地模型（约 470 MB），点击“建立 / 更新索引”，随后检索和核对原文。
5. 使用期间保持启动窗口打开，完成后在该窗口按 **Ctrl+C**。这会停止本次应用及其后台索引任务。

这是源码启动器，仍需先安装 Python。Windows ARM64、32位 Python 和免 Python 的独立 EXE 安装包尚未验证或提供。不要把其他电脑的 `.venv` 直接搬过来；各平台应重新创建运行环境。论文和索引保存在自己的电脑，不会随代码更新上传。

### 可选：PowerShell 命令

先在项目目录打开 PowerShell。启动器也可从这里运行：

```powershell
& '.\Start Web.bat'
# 换端口
& '.\Start Web.bat' --port 8766
```

手动创建环境并导入原有 PDF 文件夹：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe configure.py --pdf-dir 'C:\Research\My Papers'
.\.venv\Scripts\python.exe download_model.py
.\.venv\Scripts\python.exe rag.py sync
.\.venv\Scripts\python.exe rag.py search '误报与报警后处理'
```

直接运行解释器即可，无需激活虚拟环境或修改 PowerShell 执行策略。已有配置会被保护，不会自动覆盖。Zotero 可用 `--zotero-dir "$env:USERPROFILE\Zotero"` 替代 `--pdf-dir`；非默认数据位置应填写实际路径。

生成 MCP 配置：

```powershell
.\.venv\Scripts\python.exe configure.py --print-mcp
.\.venv\Scripts\python.exe configure.py --print-mcp --mcp-client claude-desktop
.\.venv\Scripts\python.exe configure.py --print-mcp --mcp-client cursor
.\.venv\Scripts\python.exe configure.py --print-mcp --mcp-client vscode
```

第一条生成可在 **PowerShell** 执行的 Codex 注册命令；其余生成 JSON，按 [MCP 客户端说明](MCP_CLIENTS.md) 合并进客户端设置。程序不自动更改客户端配置。要另行连接网页导入库，将 `RAG_WORKSPACE` 放在第二个 MCP 条目的 `env` 中，值为项目内 `data\web` 的绝对路径。

```powershell
# 仅影响当前 PowerShell 会话；查询独立的网页导入库
$env:RAG_WORKSPACE = (Resolve-Path '.\data\web').Path
.\.venv\Scripts\python.exe rag.py status
# 恢复默认主文库
Remove-Item Env:RAG_WORKSPACE
```

### 兼容性和验证范围

- 文件锁使用 Windows 原生字节锁；已有构建未完成时会拒绝另一构建，进程退出后系统释放锁。
- PDF 上传允许解析器重新打开临时文件，处理 Windows 保留文件名；中文文件名、内容与日志使用 UTF-8。
- Windows MCP 在启动 stdio 读取前导入数值依赖，避免首次检索阻塞；模型权重仍按需加载。相关上游记录：[python-sdk#2832](https://github.com/modelcontextprotocol/python-sdk/issues/2832)。
- 后台任务使用独立进程组，退出时按本次任务 PID 停止子进程树，避免留下 PDF 解析进程。
- 每次推送/PR 在 Ubuntu 和 Windows 上运行便携及原生测试。手动触发工作流还会在全新 Windows 环境通过实际 BAT 安装依赖，下载固定版本公开模型，验证真实 PDF 解析、向量、增量同步、网页上传/检索/图像及 MCP 引用。
- Windows CI 使用 GitHub 托管 Windows Server x64 环境；普通 Windows 10/11 桌面、浏览器和所有 MCP 客户端 GUI 尚未逐一手工测试。已有 macOS 流程持续做回归检查。

## English

The target is **Windows 10/11 x64 with Python 3.12, 64-bit x86-64**. Install Python with the `py` launcher or PATH option, extract the repository into a writable local folder, then double-click **Start Web.bat**. A short project path helps avoid legacy Windows path-length limits.

The launcher creates `.venv`, installs the locked dependencies and opens the same bilingual web UI as macOS. Keep its window open while using the app. Import PDFs, explicitly download the free local model when prompted, build the index, then search and inspect source pages. Stop with Ctrl+C in the launcher window. There are no paid API calls, and no WSL, Zotero or chat client is needed.

This is a source launcher requiring Python, not a bundled or signed EXE installer. Windows ARM64 and 32-bit Python are not validated. Recreate virtual environments on each machine rather than copying `.venv` across platforms.

Use the PowerShell examples above. Windows uses `.venv\Scripts\python.exe` in place of `.venv/bin/python`; no environment activation or execution-policy change is needed. `configure.py --print-mcp` produces a **PowerShell** Codex command. Other client options produce JSON with native interpreter paths. Settings are printed, not automatically installed. Optional web-library access uses `RAG_WORKSPACE` as described in [WEB_UI.md](WEB_UI.md).

Native checks cover interprocess locking and release, background-process-tree shutdown, reserved filenames, Unicode paths/storage, and PowerShell command quoting. Windows CI also performs a fresh launcher/dependency setup and real PDF, embedding, HTTP and MCP integration tests. CI uses Windows Server x64; individual Windows 10/11 desktop and MCP-client GUIs have not all been manually exercised.

Implementation references: [Python Windows file locks](https://docs.python.org/3.12/library/msvcrt.html), [temporary-file reopening](https://docs.python.org/3.12/library/tempfile.html), [Microsoft taskkill](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill).
