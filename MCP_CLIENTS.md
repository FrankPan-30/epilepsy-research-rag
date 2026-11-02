# Connect an MCP client / 连接 MCP 客户端

Build the library first using either PDF-folder or Zotero setup in the [README](README.md). All clients launch the same local `mcp_server.py` over **stdio**. The server retrieves evidence; the client supplies the answer model. No API key is required by this MCP server.

先按照[中文指南](README.zh-CN.md)建立 PDF 或 Zotero 索引。所有客户端运行同一个本地服务，客户端自己的模型负责回答。检索服务不需要生成 API key；云端回答按对应账户处理数据和计费。

## Generate settings / 生成配置

Run inside your clone. Each command prints the correct absolute paths and offline-model environment variables; none writes to a client configuration file.

在克隆目录运行下列命令。输出包含绝对路径及离线加载环境变量；仅打印，不会覆盖已有客户端配置。

| Client | Command | Destination / 操作 |
|---|---|---|
| Codex (existing setup) | `.venv/bin/python configure.py --print-mcp` | Execute the printed `codex mcp add` command; existing registrations still work / 执行输出命令，已有连接继续有效 |
| Claude Desktop | `.venv/bin/python configure.py --print-mcp --mcp-client claude-desktop` | Merge `mcpServers.epilepsy_research` into `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS; fully quit and reopen / 合并配置并完全退出重启 |
| Cursor | `.venv/bin/python configure.py --print-mcp --mcp-client cursor` | Merge into project `.cursor/mcp.json` or user `~/.cursor/mcp.json` / 合并到项目或用户配置 |
| VS Code Local harness, compatibility format | `.venv/bin/python configure.py --print-mcp --mcp-client vscode` | Merge `servers.epilepsy_research` into `.vscode/mcp.json`; includes `type: stdio` / 使用兼容格式 |
| Other clients using `mcpServers` | `.venv/bin/python configure.py --print-mcp --mcp-client generic` | Follow the client's local-server settings / 按客户端本地服务说明接入 |

The Claude Desktop location and local-server launch pattern follow the [MCP SDK host guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/). Cursor configuration follows its [official MCP guide](https://cursor.com/docs/mcp). VS Code now also offers portable `mcpServers` destinations; `.vscode/mcp.json` is a compatibility destination for its Local harness. Choose the destination appropriate to your harness using [VS Code's official guide](https://code.visualstudio.com/docs/agent-customization/mcp-servers). `--mcp-client generic` prints the portable structure; do not paste a `servers` object into a `mcpServers` destination.

VS Code 也提供以 `mcpServers` 为顶层键的便携配置；`.vscode/mcp.json` 是 Local harness 的兼容入口。请按官方文档选择位置，不要混用 `servers` 和 `mcpServers`。本项目仍以 macOS / Linux 为运行环境，Windows 原生文件锁尚未适配。

Merge only this server entry when other servers already exist. The existing registration stays `epilepsy_research`; use distinct client-side entry names if you register separate clones for different libraries. Moving a clone or recreating its virtual environment may require regenerating the paths. Tool execution permissions are controlled by the client.

已有其他服务时只合并本项目条目。克隆目录移动后重新生成路径；工具执行权限由各客户端管理。

## Verify / 验证

1. Run `.venv/bin/python rag.py status` and a CLI search to confirm the index and model exist.
2. Run `.venv/bin/python check_mcp.py` to exercise the actual stdio protocol, all nine tool declarations, search, full-page text and a PDF image. This needs at least one successfully indexed PDF.
3. Open the client, confirm it lists `epilepsy_research`, and ask it to call `knowledge_status`.
4. Ask for a literature search with original PDF pages, then ask it to inspect one returned page with `read_pdf_page` or `view_pdf_page`.

先检查索引与命令行搜索，再检查 stdio 协议，最后在客户端中确认工具列表、检索和引用。PDF 图像显示取决于客户端及其模型能力；可使用原文件路径手动查看。

The SDK transport and tools are tested, including PDF-folder and existing Zotero corpora. Generated configuration structures are tested. Claude Desktop, Cursor and VS Code desktop UIs have **not** each been manually exercised; a correct configuration is not a claim of end-to-end UI certification.

已测试协议、工具调用和生成配置结构；尚未逐个手动验证其他客户端桌面界面。

## Troubleshooting / 常见问题

- **No tools:** check the absolute Python/server paths and that dependencies are installed in that virtual environment. Reload the client after changing its settings.
- **No index/model:** configure your source, download the local model once, and run `rag.py sync` before asking for literature.
- **Different libraries:** each registered server points to a clone and that clone's `config.json` / `data/`. Confirm `knowledge_status` before using results.
- **Remote-only clients:** this release exposes stdio, not an HTTP endpoint. An HTTPS deployment or bridge, authentication and its data-access scope would be a separate setup.
- **Direct terminal launch looks idle:** a stdio server waits for MCP protocol messages; it is not an interactive chat command.

工具不显示时先检查绝对路径和虚拟环境；检索失败时检查模型和索引；引用库不对时核对连接指向的克隆目录。仅支持远程 HTTP 的客户端需要另行部署，本版本不会自动开放端口或上传文献。
