# Share the project

These are optional launch drafts. Adapt them to the community and its posting rules. No outreach is automated.

## English

**I built a Zotero + MCP toolkit for source-grounded seizure-prediction literature research**

I kept running into a practical problem: papers use different validation protocols and alarm rules, so a method summary is only useful if I can trace it back to the original page.

Epilepsy Research RAG indexes a local Zotero collection, combines keyword and multilingual semantic retrieval, and exposes source passages and PDF pages to Codex through MCP. PDFs and the index stay local; retrieved evidence is sent to Codex for cloud analysis. It also separates paper evidence, personal notes and project guidance.

There is a dependency-free synthetic keyword-search demo, so you can try the retrieval flow without uploading papers, downloading a model or providing an API key. The full pipeline has been exercised on macOS; broader installation feedback is welcome.

Repo: https://github.com/FrankPan-30/epilepsy-research-rag

I would especially value feedback from EEG/seizure-prediction researchers and Zotero/MCP users: which protocol details do you find hardest to compare across papers?

## 中文

**开源了一个 Zotero + MCP 科研文献检索工具，面向癫痫预测的方法比较**

做癫痫预测时，经常遇到同一个问题：论文的验证划分、报警后处理、FA/h 定义不同，只看摘要或指标很难判断方法能否迁移。

这个项目把本地 Zotero 文献整理成可追溯的检索库，支持中英文混合检索、PDF 页码与原图核查，并通过 MCP 交给 Codex 总结。PDF 和索引保存在本地，检索出的证据交给云端模型分析；论文证据、个人笔记和项目规则分别标记。

仓库提供无需安装依赖、论文、模型或 API key 的合成演示。完整流程已在 macOS 上运行，欢迎反馈其他环境安装情况，以及你最需要对比的研究字段。

项目：https://github.com/FrankPan-30/epilepsy-research-rag

## A focused launch sequence

1. Record a short run of the synthetic demo; avoid displaying your private library.
2. Share one concrete workflow with relevant colleagues or a community that welcomes project posts.
3. Ask for a specific kind of feedback, such as alarm-protocol comparison or installation experience.
4. Use reproducible reports to improve the next release. Share the improvement with the original discussion when appropriate.

Candidate audiences: Zotero users, MCP tool builders, and EEG or seizure-prediction researchers. Avoid identical mass posts or unrelated issue comments. Do not promise research accuracy or a clinical capability that has not been evaluated.
