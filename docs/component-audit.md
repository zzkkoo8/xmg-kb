# 组件选型审计

## 1. 选型标准

按以下顺序评估：

1. 可自托管；
2. 成熟、持续维护；
3. 开源许可证优先；
4. API 稳定；
5. 生产运维可落地；
6. 易开发、打包、升级；
7. 数据可迁移、可追溯；
8. 尽量减少自研；
9. 可通过 Adapter 替换，不侵入核心知识模型。

## 2. Human Wiki

### 默认：BookStack

结论：采用为当前 Canonical Wiki 基线。

原因：

- Self-hosted；
- MIT；
- 人类 Web 阅读/编辑成熟；
- WYSIWYG / Markdown 使用体验可满足知识维护；
- 层级、Search、Attachment、History、Permission；
- REST API；
- Webhook/事件能力；
- Backup/Restore 运维路径清晰；
- 适合通过薄 `WikiAdapter` 提供 AI 受控读写。

AI 不直接操作 BookStack 数据库。标准路径：

```text
xmg-kb API / MCP
→ WikiAdapter
→ BookStack REST API
```

### Outline

不作为当前默认主链。

原因：

- 当前许可证属于 source-available，不是本项目“开源优先”基线的首选；
- 项目当前尚未形成必须保留的 Outline 生产数据；
- 继续把 Outline 作为 Phase 1 硬依赖会增加后续替换成本。

如果未来部署环境接受其许可证且实测 UX/API/MCP 明显更适合，可通过独立 ADR + Adapter + Migration Benchmark 重新引入。

### Docmost

保留候选，不作为当前默认。任何替换必须重新验证稳定 API、许可边界、Backup/Restore 和 AI 读写合同。

## 3. Workflow：Prefect

结论：采用。

负责 Flow/Task、Retry、Cache、Schedule、Concurrency、Server/Worker 和 Durable State。

xmg-kb 不自研 Workflow Runtime；业务判断进入 Policy，执行进入 Adapter。

## 4. Document Parsing

### Docling Serve

结论：主 Parser。

采用异步任务：

```text
submit → task_id → poll → result
```

### MinerU

结论：Fallback。

用于扫描件、复杂布局、表格、公式、OCR 或 Docling 低质量结果。它不替代主 Parser，也不作为所有文档默认路径。

### LibreOffice

用于旧 Office 文档标准化转换，避免自研 Office Parser。

### ClamAV

用于 Evidence 扫描；不得因为扫描结果自动删除/修改原始资料。

## 5. Production RAG：RAGFlow

结论：采用。

承担 Canonical 内容的 Parser、Chunker、Indexer、Full-text / Vector / Hybrid Retrieval 与 Rerank 能力。

Production Dataset 只允许 Canonical Wiki；Raw、Legacy、Review 和 Normalized 必须隔离。

xmg-kb 不自研第二套 Vector DB、Chunk Engine 或 Hybrid Search Engine。

## 6. Observability / Evaluation：Langfuse

结论：采用，但不作为最早知识主链 Gate 的唯一阻塞条件。

作用：Trace、Feedback、Dataset、Experiment、Evaluation。

只产生质量/Evolution Signal，不作为知识事实源。

## 7. Knowledge Engineering

### Simple Curator

结论：Baseline。

作用：Section → KU → Candidate → Relation → Conflict/Cluster → Canonical Proposal。

保持薄、可测试、可替换。

### OpenSPG/KAG

结论：Optional POC。

只有同数据集 Benchmark 证明明显提升 KU Accuracy、Alignment、Conflict Discovery 或 Canonical Quality，且运维成本可接受时才 ADOPT。

## 8. API / MCP

### xmg-kb API

结论：正式产品能力。

提供 Knowledge API 与 Retrieval API，隔离外部系统与 BookStack/RAGFlow 内部实现。

### xmgkb-mcp

结论：薄层自研。

只封装 xmg-kb API/Adapter 的安全能力，不实现通用 MCP Runtime。

默认工具：Knowledge Search/Read/Source、RAG Search/Context、Review Create/Patch/Comment。

## 9. Adapter 基线

```text
SourceAdapter
ParserAdapter
WikiAdapter
RagAdapter
ObservabilityAdapter
```

新增或替换组件优先通过 Adapter / Registry 实现。

## 10. Packaging

xmg-kb 分发采用：Pinned upstream images、Component-specific deployment、`uv` Python package、Project CLI/Make、Synthetic fixtures、`.env.example`、CI、Public Safety Gate。

禁止 fork 上游组件形成私有发行版，除非有独立 ADR 证明必要。

## 11. 当前官方参考

- BookStack: https://www.bookstackapp.com/
- Prefect: https://github.com/PrefectHQ/prefect
- Docling: https://github.com/docling-project/docling
- Docling Serve: https://github.com/docling-project/docling-serve
- MinerU: https://github.com/opendatalab/MinerU
- RAGFlow: https://github.com/infiniflow/ragflow
- Langfuse: https://langfuse.com/docs
- KAG/OpenSPG: https://github.com/OpenSPG/KAG
