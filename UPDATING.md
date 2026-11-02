# 持续更新

## 更新项目代码

仓库位置是运行 RAG 的目录。在该目录操作：

```bash
git status
git pull --ff-only
# 修改代码、工作流或配置模板
.venv/bin/python -m unittest tests.UnitTests -v
# 已有本地文库时执行完整检查
.venv/bin/python validate.py
git diff
git add <本次修改的文件>
git commit -m "Describe the change"
git push origin main
```

先处理未提交改动，再拉取其他电脑的更新；不要用强制推送覆盖远端历史。复杂改动可使用 `codex/` 前缀分支，通过 PR 合并。修改依赖时同时更新 `requirements.txt` 和经验证的锁文件；更新检索模型后重新构建索引。

`git push` 是显式操作。公开仓库的 main 推送、PR 及手动触发会运行 GitHub Actions：仅检查合成演示与便携单元测试，使用公开仓库的标准 Ubuntu runner，不下载论文或向量模型，不调用 AI API，不上传构建产物。没有配置自动推送或定时同步。

## 更新论文知识库

Zotero 新增论文、附件或元数据后运行：

```bash
.venv/bin/python rag.py sync
.venv/bin/python rag.py status
```

这会更新本机 `data/`，复用未变化的解析和向量。论文全文、索引、实验记录不会随 Git 推送。修改 `knowledge/` 后也需要 `sync`，使检索索引采用新内容。

## 换电脑或恢复

1. 克隆仓库，按 README 安装环境并生成本地配置。
2. 恢复或同步自己的 Zotero 文库及 PDF 附件，确认配置的集合名称/key。
3. 下载固定版本模型并运行 `sync` 重建。
4. 需要保留人工核对记录或实验历史时，另外迁移 `data/reviews/` 和 `data/experiments/`。这些是个人资料，不在 GitHub 源码仓库中。
5. Zotero item key 变化后，调整本地检索验收案例。更换 PDF 后重新检查对应证据。

## 更新验收案例

`evaluation_cases.json` 的 8 个样例对应最初建立的个人 Zotero 文库；它们是开发样例，不能代表新文库准确率。增加经过原文核对的新案例时，保存论文标识、页码和原文锚点，并将独立验收问题与用于调优的问题区分。

修改检索代码通常不需要重新解析 PDF；修改分块、解析、模型或工作流内容后应运行 `sync`，必要时更新相应缓存版本标识。
