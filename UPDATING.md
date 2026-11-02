# 持续更新

## 更新项目代码

仓库位置是运行 RAG 的目录。在该目录操作：

```bash
git status
git pull --ff-only
# 修改代码、工作流或配置模板
.venv/bin/python -m unittest tests.UnitTests tests.PDFSourceTests test_web -v
# 完整依赖和模型已安装时，检查独立 PDF 流程
.venv/bin/python -m unittest test_pdf_pipeline test_web_pipeline -v
# 原始 Zotero 开发文库的完整检查（含固定验收 key）
.venv/bin/python validate.py
git diff
git add <本次修改的文件>
git commit -m "Describe the change"
git push origin main
```

先处理未提交改动，再拉取其他电脑的更新；不要用强制推送覆盖远端历史。复杂改动可使用 `codex/` 前缀分支，通过 PR 合并。修改依赖时同时更新 `requirements.txt` 和经验证的锁文件；更新检索模型后重新构建索引。

`git push` 是显式操作。公开仓库的 main 推送、PR 及手动触发会运行 GitHub Actions：仅检查合成演示与便携单元测试，使用公开仓库的标准 Ubuntu runner，不下载论文或向量模型，不调用 AI API，不上传构建产物。没有配置自动推送或定时同步。

## 更新论文知识库

PDF 文件夹或 Zotero 中新增/移除论文、更新附件或元数据后运行：

```bash
.venv/bin/python rag.py sync
.venv/bin/python rag.py status
```

这会更新本机 `data/`，复用未变化的解析和向量。论文全文、索引、实验记录不会随 Git 推送。修改 `knowledge/` 后也需要 `sync`，使检索索引采用新内容。

旧配置未指定 `library_source` 时继续按 Zotero 读取。文件夹模式设为 `pdf_folder`，并填写 `pdf_dir`；PDF 内容相同的副本合并，改名保留 ID，修改 PDF 字节产生新 ID。可选的 `*.pdf.json` 元数据文件随原件另行保存。空 PDF 目录会拒绝同步以保护已有索引。

主 CLI/MCP 工作区维护一个活动来源；切换来源后重新 `sync` 会替换活动快照，不自动合并来源。网页导入库独立保存在 `data/web/`，可与主文库同时使用；更多文库可用独立克隆。客户端调用同一个 MCP 服务，配置说明见 [MCP_CLIENTS.md](MCP_CLIENTS.md)。

网页新增 PDF 后，在网页点击“建立 / 更新索引”。备份网页资料时保留 `data/web/uploads/`；换电脑后重新选择 PDF 建库。人工核对记录和实验记录应另外备份，详见 [WEB_UI.md](WEB_UI.md)。

## 换电脑或恢复

1. 克隆仓库，按 README 安装环境并生成本地配置。
2. 恢复 PDF 文件夹与元数据 JSON，或同步 Zotero 文库及附件；确认 `pdf_dir` 或集合名称/key。
3. 下载固定版本模型并运行 `sync` 重建。
4. 需要保留人工核对记录或实验历史时，另外迁移 `data/reviews/` 和 `data/experiments/`。这些是个人资料，不在 GitHub 源码仓库中。
5. Zotero item key 变化后，调整本地检索验收案例。更换 PDF 后重新检查对应证据。

## 更新验收案例

`evaluation_cases.json` 的 8 个样例对应最初建立的个人 Zotero 文库；它们是开发样例，不能代表新文库准确率。增加经过原文核对的新案例时，保存论文标识、页码和原文锚点，并将独立验收问题与用于调优的问题区分。

修改检索代码通常不需要重新解析 PDF；修改分块、解析、模型或工作流内容后应运行 `sync`，必要时更新相应缓存版本标识。
