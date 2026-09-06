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
8. 尽量减少自研。

## 2. Human Wiki

### 默认：Outline

结论：采用。

原因：

- 自托管；
- 长期活跃；
- 高质量协作编辑体验；
- Collections / Nested Documents；
- Search；
- Attachments；
- Document History；
- Permissions；
- Webhooks；
- API / MCP；
- Export / Import；
- 运维和安全文档成熟。

Outline 当前采用 BSL 1.1，属于 source-available 而不是严格 OSI 开源；这是 v7 明确记录的许可证例外。若未来强制 100% OSI，再通过独立 ADR 评估替代品，不在当前主链并行维护两套 Wiki。

AI 通过 API/MCP 读写 Review；Webhook Adapter 负责把审核和 Revision 变化同步回状态库。

### BookStack

不作为当前 v7 默认基线。

原因：

- 虽然 MIT 且运维成熟，但它不是当前设计已选定并配置的 Canonical Wiki；
- 切换会导致 Outline Collection、API/MCP、Webhook 和 Mapping 合同整体变化；
- 未经新 ADR 与迁移验证，不得替换当前主链。

### Docmost

不作为当前默认。

原因：

- Core 为 AGPL；
- UI 现代；
- 但需要再次验证其当前稳定版公开 API 能力与许可边界后，才适合承担“AI 稳定读写”主链。

## 3. Workflow

### Prefect

结论：采用。

官方项目使用 Apache-2.0，提供 Python-native：

- Flow / Task；
- Retry；
- Cache；
- Schedule；
- Concurrency；
- Server / Worker。

不在 xmg-kb 中自研 Workflow Runtime。

## 4. Document Parsing

### Docling Serve

结论：主 Parser。

Docling Core/Docling 为 MIT。Docling Serve 暴露异步任务接口：

```text
POST async
→ task_id
→ poll
→ result
```

并支持 `local`、`rq`、`ray` 等执行引擎，可从单机 Pilot 扩展到 Worker 架构。

### MinerU

结论：Fallback。

适用于：

- 扫描件；
- 复杂布局；
- 表格；
- 公式；
- OCR；
- Docling 低质量结果。

当前 MinerU 使用“基于 Apache 2.0 并带附加条款”的 MinerU Open Source License，分发和对外服务前必须重新审计许可证条件。

## 5. Production RAG

### RAGFlow

结论：采用。

RAGFlow 当前官方 Ingestion Pipeline 提供：

- Parser；
- Transformer；
- Chunker；
- Indexer。

Indexer 支持：

- Full-text；
- Embedding；
- Hybrid（官方推荐）。

因此 xmg-kb 不自研 Chunk Engine、Vector DB 或 Hybrid Search Engine。

Production Dataset 只允许 Canonical Wiki。

## 6. Observability / Evaluation

### Langfuse

结论：采用。

Langfuse 可自托管，核心开源能力包括：

- Tracing；
- Feedback；
- Dataset；
- Experiment；
- Evaluation。

只将其作为 Trace/Eval 和 Evolution Signal 来源，不作为知识事实源。

## 7. Knowledge Engineering

### Simple Curator

结论：必须有。

作用：

- Section → KU；
- Candidate Retrieval；
- Relation Judgment；
- Conflict；
- Canonical Proposal。

保持薄、可替换。

### OpenSPG/KAG

结论：POC。

KAG 当前 Apache-2.0，定位为专业领域知识构建与推理框架。

必须通过同一真实数据集对照实验后才能 ADOPT。

## 8. AI 标准接口

### xmgkb-mcp

结论：薄层自研。

只封装：

- Outline API/MCP；
- RAG Search；
- Provenance Lookup。

不要实现通用 MCP Runtime，使用成熟 MCP SDK。

默认只暴露安全工具。

## 9. Packaging

xmg-kb 分发：

- Pinned upstream images；
- Component-specific deployment files；
- `uv` Python package；
- Project CLI / Make；
- Synthetic fixtures；
- `.env.example`；
- CI；
- Public Safety Gate。

禁止 fork 上游组件形成私有发行版，除非有单独 ADR 证明必要。

## 10. 官方参考

- Outline: https://docs.getoutline.com/
- Outline Source: https://github.com/outline/outline
- Prefect: https://github.com/PrefectHQ/prefect
- Docling: https://github.com/docling-project/docling
- Docling Serve: https://github.com/docling-project/docling-serve
- MinerU: https://github.com/opendatalab/MinerU
- RAGFlow: https://github.com/infiniflow/ragflow
- Langfuse: https://langfuse.com/docs
- KAG/OpenSPG: https://github.com/OpenSPG/KAG
