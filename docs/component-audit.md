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

### 默认：BookStack

结论：采用。

原因：

- MIT；
- 自托管；
- 长期活跃；
- WYSIWYG + Markdown；
- Books / Chapters / Pages；
- Search / Tags；
- Attachments；
- Page History；
- Permissions；
- Webhooks；
- 内置 REST API；
- Export / Import；
- 运维和安全文档成熟。

BookStack API 文档随实例提供在 `/api/docs`，自动化使用受权限约束的 API Token。

AI 通过 REST API 读写 Review；标准 Agent 入口通过薄 `xmgkb-mcp` Adapter 暴露。

### Outline

不作为默认开源基线。

原因：

- UX 和第一方 API/MCP 很强；
- 但当前 BSL 1.1 明确不是 Open Source License。

如果部署环境接受 Source-Available，可作为 Alternative Profile。

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

- BookStack REST API；
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

- BookStack: https://www.bookstackapp.com/docs/
- BookStack Source: https://codeberg.org/bookstack/bookstack
- Prefect: https://github.com/PrefectHQ/prefect
- Docling: https://github.com/docling-project/docling
- Docling Serve: https://github.com/docling-project/docling-serve
- MinerU: https://github.com/opendatalab/MinerU
- RAGFlow: https://github.com/infiniflow/ragflow
- Langfuse: https://langfuse.com/docs
- KAG/OpenSPG: https://github.com/OpenSPG/KAG
