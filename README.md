# xmg-kb

xmg-kb 是一套面向企业技术资料的**知识库基础设施 / Knowledge Platform**。项目只负责知识相关能力：

- 高质量知识入库管线；
- 文档与知识治理；
- 本地文件型 Canonical Knowledge Store；
- 高质量 RAG 索引与检索；
- 面向外部应用的 Knowledge API / Retrieval API；
- 面向 AI Agent 的受控 MCP 接口；
- 知识库运行、备份、恢复、审计与质量评估。

xmg-kb **不负责具体业务 Agent、聊天机器人、工单、钉钉、运维执行或 Multi-Agent 编排**。这些系统是 xmg-kb 的外部消费者，通过 API / MCP / RAG 使用知识能力。

## 核心架构

当前阶段聚焦文件型知识库生产管线，暂缓 Wiki 展示/编辑层。知识文件及多媒体资产在本地文件系统中保存，文件是唯一 Canonical Knowledge；数据库、RAG 索引和 GitLab 都不是知识本体。

```text
多来源 Evidence / Legacy / Agent Feedback
                  ↓
         Source Registry / Manifest
                  ↓
          Prefect Ingestion Pipeline
                  ↓
    Docling Serve → MinerU / OCR fallback
                  ↓
      Normalize → Markdown + Assets + Metadata
                  ↓
  Knowledge Build / Dedup / Taxonomy / Relations
                  ↓
      Local File Knowledge Store (Canonical)
                  ↓
  Directory Governance / Quality / Provenance
                  ↓
       Knowledge API / File API / MCP
                  ↓
       External Agents / RAGFlow Index
                  ↓
       Usage Feedback → Review Proposal
                  └────────→ Knowledge Build
```

GitLab 暂不进入当前实现；未来只作为文件双向同步、版本控制和备份目标。Wiki 展示/编辑层暂缓，后续必须原生读写知识原文件，不得建立第二份 Canonical 副本。

## 七层能力模型

```text
7. Interface            REST API / MCP
6. Retrieval            RAGFlow / Hybrid / Rerank
5. Canonical Knowledge  Local Files / Markdown / Assets / Metadata
4. Knowledge Governance KU / Version / Conflict / Canonicalization
3. Document Governance  Dedup / Metadata / Taxonomy / Provenance
2. Ingestion            Prefect / Docling Serve / MinerU
1. Evidence             Raw / Legacy / External Sources
```

横向公共能力：State、Security、Audit、Observability、Backup/Restore、Config、Adapter Registry。

## 核心原则

- **Evidence != Canonical**：原始资料不是正式知识。
- **Knowledge Unit != RAG Chunk**：前者用于治理，后者用于检索。
- **Canonical Files != RAG Index**：本地知识文件是权威知识层，RAG 是可重建派生索引。
- **AI Draft != Approved Knowledge**：AI 默认只能写 Review，关键事实需审核后进入 Canonical。
- **Canonical-only Production RAG**：Production RAG 不直接索引 Raw、Legacy、Review 或临时语料。
- **Legacy First, Raw Fallback**：已有高质量成果优先复用，只有缺失/损坏/低质量内容才回原始资料重新处理。
- **成熟组件优先**：不自研 Wiki、OCR/PDF 引擎、Workflow Runtime、Vector DB、通用 Search/Trace 平台。
- **接口解耦**：外部业务项目只依赖稳定 API / MCP，不反向成为 xmg-kb 的 Phase Gate。

## 默认组件

当前不部署 Wiki。Outline、BookStack、Wiki.js 等展示层均不属于当前主链；后续选型必须证明能原生读写本地知识文件，而非只导入/导出数据库副本。

| 能力 | 默认组件 | 角色 |
|---|---|---|
| File Knowledge Store | Local filesystem | Canonical Markdown/HTML/assets, provenance, directory governance |
| Workflow | Prefect | Retry / Resume / Cache / Schedule / Concurrency |
| 主解析 | Docling Serve | 异步文档解析 |
| 复杂文档兜底 | MinerU | OCR / 复杂布局 / 表格 / 公式 |
| Legacy Office | LibreOffice | Office 格式标准化 |
| 安全扫描 | ClamAV | Evidence 扫描，不破坏源文件 |
| Production RAG | RAGFlow | Parser / Chunker / Indexer / Retrieval / Rerank |
| Trace & Eval | Langfuse | Trace / Feedback / Dataset / Evaluation |
| Knowledge Engineering | Simple Curator + KAG POC | KU / Alignment / Conflict / Canonical Proposal |
| AI 标准接口 | xmg-kb API + MCP Adapter | Knowledge / Retrieval / Review 安全接口 |

## 对外接口

xmg-kb 最终至少提供三类稳定能力：

```text
Knowledge API
- search/read canonical knowledge
- source/provenance lookup
- create/patch review
- comment/history

Retrieval API
- search/retrieve/context
- metadata filter
- citation + canonical/page/revision traceability

MCP
- knowledge_search
- knowledge_read
- knowledge_sources
- rag_search
- rag_context
- review_create
- review_patch
- review_comment
```

默认不暴露 Canonical Delete、强制覆盖、索引销毁等高风险 Tool。

## Codex 开局

新的 Codex / Agent 按顺序阅读：

1. [`AGENTS.md`](AGENTS.md)
2. [`CODEX-START.md`](CODEX-START.md)
3. [`docs/requirements.md`](docs/requirements.md)
4. [`docs/architecture.md`](docs/architecture.md)
5. [`docs/roadmap.md`](docs/roadmap.md)
6. [`docs/component-audit.md`](docs/component-audit.md)
7. [`docs/design-audit.md`](docs/design-audit.md)
8. [`docs/development.md`](docs/development.md)
9. [`docs/testing.md`](docs/testing.md)
10. [`docs/publication-policy.md`](docs/publication-policy.md)

然后以本地真实代码、运行状态、测试和最新报告为证据，只推进当前最靠前且前置条件满足的 Gate。

## 公共仓库边界

本仓库只保存公开设计、源码、Schema/Prompt、合成测试数据、部署模板、CI 和公共运维文档。

禁止提交真实知识资料、生产 Wiki 导出、解析语料、RAG Chunk/Vector Index、数据库、运行状态、内部报告、Trace、日志、备份、Secret、真实内部路径或客户/生产环境敏感信息。

详见 [`docs/publication-policy.md`](docs/publication-policy.md)。

## 文档索引

- [需求基线](docs/requirements.md)
- [总体架构](docs/architecture.md)
- [研发路线图](docs/roadmap.md)
- [组件选型审计](docs/component-audit.md)
- [历史设计审计](docs/design-audit.md)
- [数据模型](docs/data-model.md)
- [开发规范](docs/development.md)
- [部署规范](docs/deployment.md)
- [测试与验收](docs/testing.md)
- [公共仓库发布规范](docs/publication-policy.md)
- [架构决策记录](docs/decisions/README.md)

## License

xmg-kb 自有代码许可证在首次正式软件发布前单独确定；第三方组件遵循各自许可证。