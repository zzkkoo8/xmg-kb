# 需求基线

## 1. 产品定位

xmg-kb 是独立的知识库基础设施 / Knowledge Platform，只负责知识相关能力：

1. **Ingestion**：知识入库、解析、标准化与可恢复处理；
2. **Governance**：去重、元数据、版本、权威性、冲突、Knowledge Unit 与 Canonicalization；
3. **Human Wiki**：人类可读、可编辑、可审核、可维护的 Canonical Wiki；
4. **RAG**：Canonical-only 的高质量索引、检索、重排与引用；
5. **API / MCP**：向外部应用和 AI Agent 提供稳定、受控的知识接口；
6. **Operations**：状态、审计、质量评估、备份恢复与可观测性。

xmg-kb 不承担具体业务 Agent、聊天机器人、工单、钉钉、自动运维或 Multi-Agent 编排。外部项目只能作为 API/MCP/RAG 消费者，不反向成为 xmg-kb 的 Phase Gate。

## 2. 输入资料

系统面向 Markdown/HTML、PDF、DOC/DOCX、PPT/PPTX、XLS/XLSX、图片/扫描件、历史已整理知识、厂商手册、FAQ、培训、版本说明、故障案例等异构资料。

所有 Evidence 必须保留 Source ID、Hash、Provenance 和处理状态；源数据默认不可被 Pipeline 原地修改。

## 3. Human Wiki

必须满足：

- 浏览器访问；
- WYSIWYG 和/或 Markdown 编辑；
- 清晰层级与搜索；
- Tags / Attachments / Comments；
- Page History；
- Permission；
- Import / Export；
- 稳定 REST API；
- Webhook 或等价事件机制；
- Backup / Restore。

当前默认实现为 BookStack，但上层通过 `WikiAdapter` 解耦，不允许业务逻辑直接依赖 Wiki 数据库。

## 4. AI Knowledge Management

AI 通过 API/MCP 必须能够：

- Search Canonical；
- Read Full Page；
- Read Source / Provenance；
- Create Review；
- Patch Review；
- Comment；
- 提出分类、目录和合并建议。

默认禁止：

- Delete Canonical；
- 绕过 Review；
- 无证据改变关键参数；
- 静默解决版本或冲突；
- 直接操作 Wiki 数据库。

## 5. 海量入库管线

必须支持：

- Batch；
- Retry；
- Resume；
- Incremental；
- Idempotent；
- Concurrency Limit；
- per-document 状态；
- 可按文档重跑；
- Legacy First / Raw Fallback；
- Parser Quality Gate；
- Parser fallback；
- Provenance 全程保留；
- 失败隔离与可审计状态。

## 6. Document Governance

至少包含：

- Exact Dedup；
- Near-document Dedup；
- Metadata；
- Taxonomy / Alias；
- Version Scope；
- Authority；
- Security Classification；
- Provenance。

## 7. Knowledge Governance

至少包含：

- Section；
- Knowledge Unit；
- Knowledge-level Relation；
- Conflict；
- Canonical Proposal；
- Review；
- Canonicalization。

必须长期保持：`Knowledge Unit != RAG Chunk`。

## 8. RAG

Production RAG 必须：

- 只来源于 Canonical Wiki；
- Raw / Legacy / Review / Normalized 不进入 Production Dataset；
- 有正式 Chunking；
- Chunk 可追溯至 Canonical ID + Wiki Page + Revision；
- Metadata Filter；
- Full-text；
- Vector；
- Hybrid；
- Rerank；
- Incremental Update；
- Revision Atomic Switch；
- Citation；
- Gold QA Benchmark。

## 9. 对外 API

至少形成稳定的逻辑接口：

### Knowledge API

- Search / Read Canonical；
- Source / Provenance Lookup；
- History；
- Create/Patch Review；
- Comment。

### Retrieval API

- Search；
- Retrieve；
- Context；
- Metadata Filter；
- Citation；
- Canonical/Page/Revision Traceability。

接口必须与具体外部业务 Agent 解耦。

## 10. MCP

MCP 是 xmg-kb API/Adapter 的标准 AI 接口，不重新实现一套业务逻辑。

默认安全 Tool：

- `knowledge_search`
- `knowledge_read`
- `knowledge_sources`
- `rag_search`
- `rag_context`
- `review_create`
- `review_patch`
- `review_comment`

默认不暴露 Canonical Delete、强制覆盖、索引销毁等高风险 Tool。

## 11. 质量目标

初始目标：

- Canonical Source Traceability = 100%；
- Critical Wrong Merge = 0；
- Top-5 Retrieval Recall >= 95%；
- Critical Top-5 Recall >= 98%；
- Citation Correctness >= 95%；
- Correct Refusal >= 98%；
- Critical Hallucination = 0。

阈值应通过真实 Gold QA 持续校准，而不是硬编码为永远不变的产品参数。

## 12. Knowledge Evolution

真实使用信号至少分类：

- `GOOD`
- `WEAK`
- `MISSING`
- `CONFLICT`
- `OUTDATED`
- `FRAGMENTED`

系统可自动聚类、找证据和生成 Review Proposal，但不能绕过 Review 直接改变关键 Canonical 技术事实。

## 13. 工程要求

- Self-hosted；
- 成熟开源组件优先；
- Harness/Adapter 思想，组件可替换；
- 版本可锁定；
- 开发环境可复现；
- 运行数据与 Git checkout 分离；
- 公共代码可在无私有知识数据时安装和测试；
- 组件可独立升级；
- 不依赖真实私有目录结构；
- 公共仓库零内部数据；
- 高风险知识写操作必须可人工审核。