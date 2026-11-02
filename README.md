# 癫痫预测科研 RAG

本地文献与索引 + Codex 云端分析。优先服务文献检索和方法总结，并支持项目知识、评价规范、模型诊断和实验设计。程序没有调用付费生成或向量 API；模型文件首次公开下载，运行时离线加载。

## 首次安装或换电脑

当前已验证环境为 macOS Apple Silicon、Python 3.12。运行时使用本地模型，首次安装需要联网下载依赖与公开模型。Windows 原生环境尚未适配（文件锁使用 `fcntl`）。

```bash
git clone https://github.com/FrankPan-30/epilepsy-research-rag.git
cd epilepsy-research-rag
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python configure.py --zotero-dir "$HOME/Zotero" --collection-name '癫痫预测'
.venv/bin/python download_model.py
.venv/bin/python rag.py sync
```

`configure.py` 创建本机的 `config.json`，后续 Git 更新不会覆盖它。同名集合不唯一时，设置 `collection_key`。已有配置时直接编辑该文件，初始化命令会保护它。

接入 Codex：运行下面的命令，复制它输出的 `codex mcp add ...` 命令执行。它会按当前克隆位置生成正确路径。若已有同名连接，先检查现有配置再决定是否更换。

```bash
.venv/bin/python configure.py --print-mcp
```

当前电脑原有项目连接可以继续使用。项目不自动修改全局 Codex 配置。

## 使用

在 Codex 中说：

> 检索我的癫痫预测知识库，总结跨患者研究的报警后处理方法，核对评价协议并引用原文页码。

项目 MCP 名称为 `epilepsy_research`。如当前会话尚未加载 MCP，直接使用以下命令，结果同源。

```bash
.venv/bin/python rag.py status
.venv/bin/python rag.py search '跨患者预测中的误报和报警后处理' --limit 8
.venv/bin/python rag.py paper ZOTERO_ITEM_KEY
.venv/bin/python rag.py read CHUNK_ID --neighbors 1
.venv/bin/python rag.py catalog --field alarm_postprocessing
.venv/bin/python rag.py sync
```

`paper` 中填写真实 Zotero 条目 key，`read` 中填写本次检索返回的数字 ID。引用需保留返回的 generation；更新后重新检索，避免旧 chunk ID 对应不同内容。

## 内容与证据

- 范围：配置中的 Zotero 集合和全部子集合。按 item key 去重，排除回收站、独立附件和独立笔记；DOI/标题的跨条目重复仍需人工审核。
- 使用 SQLite 只读事务读取一致快照。此路线是已确认本机 API 无响应时的回退，不直接写 Zotero。
- PDF 原件继续由 Zotero 保存。解析缓存保存逐页 Markdown、页码、表格/图片位置和 SHA256；首次解析及字段匹配均标记未人工核验。
- 只有摘要的记录标为 `metadata`；用户笔记与批注明确标记，默认论文搜索不混入个人批注或项目规范。
- 实验字段是关键词定位的证据目录，而非已经确认的研究分类或自动归一化指标。缺失字段表示尚未定位到证据。
- `data/reviews/` 保存已对照原文检查的局部方法描述，标明助手核对范围、是否经过人工复核、PDF哈希和原文位置。其状态不扩展到整篇论文；更换PDF后需要重新核对。
- 原图查看工具 `view_pdf_page` 可核查公式、结构图和表格。公式不保证准确转成 LaTeX；低文本量及疑似图片表格页使用本地 RapidOCR 补充识别，识别文字与位置单独保存并标记需视觉核查。OCR 行文本不作为已恢复的表格列结构。
- 全文分块遵循章节/页边界，以 E5 tokenizer 控制到 420 tokens、重叠 45 tokens；长表格可能跨块，核对时读取完整页并查看原图。
- 中英混合检索使用 SQLite FTS5、领域查询扩展、多语言 E5 与 RRF 排序融合。RRF 是排序融合，并非独立神经重排序模型。模型分数不是可信度概率。
- 每篇最多返回三个候选片段（指定论文时放宽）。复杂问题应多轮检索和展开完整页面。系统比较先枚举全集并逐篇检查，不能把 top-k 当作全部证据。

## 四类研究支持

`knowledge/` 是项目工作规则，明确标记为非论文证据。五个工作流包括文献检索、项目管理、数据与评价、模型诊断、实验设计。既有训练代码、实验结果和个人文件尚未批量入库。

实验记录通过 `experiments.py` 显式保存，按版本保留历史：

```bash
.venv/bin/python experiments.py template
.venv/bin/python experiments.py save /absolute/path/record.json
.venv/bin/python experiments.py list
```

模板只是待填写结构，不代表已完成实验。窗口与事件指标分别存储。保存已完成实验需要代码版本与结果路径。

## 更新与复现

代码更新和文库更新分别管理：GitHub 保存程序、工作流和重建材料；`sync` 更新本机知识库。具体提交、推送、跨电脑恢复步骤见 [UPDATING.md](UPDATING.md)。仓库可持续推送，当前没有自动推送或定时运行。

`sync` 手动读取当前集合：PDF 哈希未变时复用解析，文本和模型版本未变时复用向量。新的索引写入独立 generation，全部完成后原子切换 `data/current.json`。构建失败时原有索引继续可用；并发构建通过文件锁拒绝。

旧 generation 可作为回滚材料；确认无依赖后再清理。移出集合的条目不会进入新索引；旧版本和缓存仍保留到显式清理。索引是某次快照，`status` 显示完成时间。

首次复现：创建独立虚拟环境，安装 `requirements.lock.txt`，运行 `download_model.py` 下载固定 revision 的公开模型，再运行 `sync`。本机 `.venv` 复用了已安装的 PyTorch/NumPy，锁文件包含实际使用版本。

## 费用和数据边界

本地解析、向量生成和检索不调用云端 API。Codex 接收到检索证据后在当前聊天中分析。后续若增加独立云端全文提取、OCR或生成服务，必须先向用户说明用途和预计费用。

`data/`、`models/`、`.venv/`、`config.json` 和本机 `mcp_config.toml` 均被 Git 忽略。原始 PDF 不复制入代码库。文献正文中的指令不执行。

## 验证

新克隆没有私人论文，也可以运行无需文库的配置与记录测试：

```bash
.venv/bin/python -m unittest tests.UnitTests -v
```

全库测试与检索开发样例需要本机文献。`evaluation_cases.json` 中的条目 key 属于首期文库；换成其他文库后应建立自己的原文锚点案例。

在本仓库目录运行 `.venv/bin/python validate.py` 完成验证。`tests.py` 检查引用定位、分块 token 上限、来源隔离、实验记录校验和离线检索；`evaluate.py` 检查8个附原文锚点的检索案例；`check_mcp.py` 验证实际MCP工具连接、查询和图像返回。另有22个研究验收问题供实际使用中核对，合计30题，尚未把未核对问题计入准确率。报告保存在 `data/validation/`。自动检查与小样本案例只验证相应范围，全文解析、全部字段及科研建议仍需阅读原文和实际实验验证。

方法依据：[E5 模型卡](https://huggingface.co/intfloat/multilingual-e5-small)、[PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM)、[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)。
