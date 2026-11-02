# Local web interface / 本地网页

## English

### Open and use

Install Python **3.12** from [python.org](https://www.python.org/downloads/), unzip the project or update your clone, then double-click **Start Web.bat** on Windows x64 or **Start Web.command** on macOS. The launcher creates `.venv` and installs missing dependencies from `requirements.lock.txt`. The initial installation needs an internet connection and may take several minutes. This is a source-based launcher; it is not a bundled Python runtime or signed desktop application.

On Linux, run `bash start_web.sh`. An existing environment can start directly with `.venv/bin/python web_app.py`. See [WINDOWS.md](WINDOWS.md) for Windows setup and PowerShell paths. Full pipelines are tested on macOS Apple Silicon and in native Windows CI; Ubuntu CI covers portable tests.

Keep the launcher window open. It opens a browser at `127.0.0.1:8765` with a temporary session link. If automatic opening fails, copy the **full link** printed there. Use Ctrl+C in that window to stop the app. To choose another port, use `bash start_web.sh --port 8766`.

1. **Import:** Choose multiple PDFs, choose a folder (including subfolders), or drag PDF files into the import area. Each PDF may be up to 100 MB. Exact copies are skipped; different versions are separate records. Folder upload selects PDF files only, not metadata sidecars. Titles/authors come from embedded metadata, with filename fallback for titles; no automatic bibliographic lookup is performed.
2. **Build:** If needed, explicitly download the free public local model (about 470 MB), then click **Build / update index**. Watch the status and expand run details for diagnostics. After adding papers, build again. Unchanged parsing and vectors are reused. A failed build keeps the previous active index.
3. **Search:** Enter Chinese or English text. Semantic + keyword search supports cross-language retrieval; keyword-only search uses literal terms plus domain query expansion. Results are a ranked selection, not an exhaustive review. Browse all papers for the catalog, including entries with no extracted full text.
4. **Verify:** View source renders the original PDF page locally. Previous/Next changes pages; Copy citation includes the title and current PDF page; Download PDF saves the original file. PDF page numbers may differ from printed journal page labels. OCR and table text need checking against the image.

Use **English / 中文** to switch the interface, including existing result labels. The browser remembers the choice. Paper content and raw diagnostic logs keep their original language. The UI retrieves evidence; it does not generate AI answers or automatically translate papers.

### Your two libraries

| Choice | Data | Updating |
|---|---|---|
| Web imports | Local PDF copies in `data/web/uploads/`; index/cache in `data/web/data/`; settings in `data/web/config.json` | Import and build in the browser |
| Existing library | Your existing main `config.json` and `data/`, using a PDF folder or Zotero | Existing `rag.py sync` workflow |

The web app does not rewrite your main configuration, index or MCP registration. Web uploads are always added to the web library, even when you were browsing the existing library. Both are excluded from Git; pushing code never uploads papers, indices or personal configurations. Uploaded copies use additional disk space equal to the PDFs, plus extracted text, caches and vectors. The local model is shared.

The first web launch copies relevant main/default retrieval settings into its own configuration. Later main-configuration changes do not automatically update that copy. To remove a web paper for now, stop the app, remove its hash-named folder from `data/web/uploads/`, and rebuild; there is no delete button in this version. An empty library build is rejected to avoid accidentally replacing the last usable index. Old snapshots/caches require deliberate cleanup.

For backup, preserve original PDFs or `data/web/uploads/`. On another computer, import those PDFs and rebuild. Also preserve any manually created review/experiment records separately; indices contain absolute paths and are best rebuilt after relocation.

### Optional: connect web imports to an MCP client

Your existing MCP connection continues to use the main library. To expose the web library as a **second** stdio server, use the same Python and `mcp_server.py` paths, a different server name, and add this environment variable to that server's configuration:

```json
{
  "RAG_WORKSPACE": "/absolute/path/to/epilepsy-research-rag/data/web"
}
```

Place it in the entry's `env` object. See [MCP_CLIENTS.md](MCP_CLIENTS.md) for client-specific structure. CLI example:

```bash
RAG_WORKSPACE='/absolute/path/to/epilepsy-research-rag/data/web' .venv/bin/python rag.py status
```

Build the web index first. No connection is changed automatically. The loopback web server is separate from stdio MCP; it is not a hosted MCP endpoint.

### Troubleshooting and costs

- **Session expired:** reopen the full link from the current launcher window. Restarting the app creates a new session.
- **No index / model:** import PDFs, download the model if prompted, then build. A first model download needs internet; parsing, embeddings and search then run locally.
- **No matches:** check the selected library; try semantic search or source-language keywords. Scanned/image-heavy PDFs may need OCR and may still yield incomplete text.
- **PDF changed / library updated:** rebuild when the source changed, then rerun the search before opening the citation. The viewer checks the index version and PDF hash.
- **Build failed:** expand Run details. Unreadable/password-protected uploads are rejected. A built library may report extraction failures for accepted files; inspect the log and originals.
- **Port occupied:** close the previous launcher, or use another port. The app only binds `127.0.0.1`, checks API sessions and origins, and is intended for one local user. Do not expose it through a public reverse proxy.

There are **no paid API calls** in this interface. Dependencies and model weights need initial downloads. Optional answers in a separate MCP client follow that client's subscription or API pricing.

## 中文

### 打开与使用

先安装 [Python 3.12](https://www.python.org/downloads/)，解压项目或更新已有克隆，Windows x64 双击 **Start Web.bat**，macOS 双击 **Start Web.command**。启动器会创建 `.venv`，根据 `requirements.lock.txt` 安装缺失依赖；首次需联网，可能耗时几分钟。这是源码启动器，尚未捆绑 Python 运行时或打包为签名桌面应用。

Linux 运行 `bash start_web.sh`；已有环境可直接运行 `.venv/bin/python web_app.py`。Windows 安装和 PowerShell 命令见 [WINDOWS.md](WINDOWS.md)。完整流程在 macOS Apple Silicon 和原生 Windows CI 验证，Ubuntu CI 执行便携测试。

使用期间保持启动窗口打开。浏览器会打开带临时会话的 `127.0.0.1:8765` 地址；未自动打开时，复制窗口中的**完整链接**。在启动窗口按 Ctrl+C 停止。端口冲突可用 `bash start_web.sh --port 8766` 换端口。

1. **导入：**选择多个 PDF、选择文件夹（含子目录），或拖入 PDF 文件。每份最多 100 MB；相同文件跳过，不同版本分别入库。文件夹上传只取 PDF，不导入元数据 JSON。标题和作者来自 PDF 内嵌信息，标题缺失时使用文件名；不会自动联网补全文献信息。
2. **建库：**首次按提示下载免费本地模型（约 470 MB），再点击“建立 / 更新索引”。可展开运行详情查看过程。新增文献后再次建立索引；未变更的解析和向量会复用，构建失败保留原有活动索引。
3. **检索：**可输入中文或英文。语义 + 关键词支持跨语言检索；仅关键词模式使用词项及领域查询扩展。排名结果是候选证据，系统比较还需浏览文献目录并逐篇核查。目录包含没有可用全文的记录。
4. **核查：**“查看原文”在本机渲染 PDF 页面，支持翻页、复制带当前页码的引用及下载原件。PDF 页序可能与期刊印刷页码不同，OCR 和表格文本需对照原图。

右上角 **English / 中文** 同时切换界面和已有结果标签，浏览器记住语言选择。论文内容和原始技术日志保持原语言。网页提供证据检索，不生成 AI 回答或自动翻译全文。

### 两个文库与原有用法

- **网页导入库：**PDF 副本在 `data/web/uploads/`，索引与缓存为 `data/web/data/`，独立设置为 `data/web/config.json`。在网页中导入、更新。
- **现有文库：**继续使用原来的 `config.json`、`data/` 及 PDF 文件夹/Zotero 来源，通过既有 `rag.py sync` 更新。

网页不会重写主配置、索引或 MCP 注册；即使当前浏览“现有文库”，新上传也进入网页导入库。两者均被 Git 忽略，不随代码上传。网页副本额外占用与 PDF 总大小相当的空间，另加文本、缓存和向量；模型权重共用。

首次启动会从主配置/默认值复制检索参数，之后主配置变更不会自动同步到网页配置。当前没有网页删除按钮：需要移除论文时，停止应用，移除 `data/web/uploads/` 中对应的哈希目录后再建库。空库构建会被拒绝，以保护最后可用的索引；旧快照与缓存需要明确清理。

备份原始 PDF 或 `data/web/uploads/`；换电脑后重新导入建库。手工核对记录和实验记录另行保留，索引中的绝对路径不适合直接跨电脑搬用。

### 可选：让 MCP 客户端使用网页文库

既有 MCP 连接继续指向主文库。要把网页文库作为第二个服务，在相同 Python/`mcp_server.py` 配置下使用不同服务名称，并在该条目的 `env` 中加入上文的 `RAG_WORKSPACE`，指向项目内 `data/web` 的绝对路径。先在网页完成建库，再连接。结构参考 [MCP_CLIENTS.md](MCP_CLIENTS.md)。程序不会自动更改客户端设置；网页服务器与 stdio MCP 是两个入口。

### 常见问题与费用

- **会话失效：**用当前启动窗口中的完整链接重新打开；每次重启会生成新会话。
- **没有索引/模型：**先导入、下载模型，再建库。首次下载需联网，之后本地完成解析与检索。
- **找不到内容：**检查当前文库，尝试语义检索或原文关键词。扫描 PDF 可能需要 OCR，提取结果仍需核验。
- **原文或文库已变更：**更新索引后重新检索，再打开引用；程序检查索引版本与 PDF 哈希。
- **构建失败：**展开“运行详情”。损坏或加密上传会被拒绝；已接受的 PDF 如在解析阶段失败，会显示失败数量，需检查日志和原件。
- **端口占用：**关闭之前的启动窗口，或换端口。仅监听 `127.0.0.1`，带会话和来源校验，适用于本机单用户，不要通过公网反向代理暴露。

网页**不调用付费云端 API**。首次下载依赖和公开模型；另用 MCP 客户端生成回答时，费用依其订阅或 API 规则。
