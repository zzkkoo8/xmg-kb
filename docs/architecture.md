# 总体架构

## 1. 架构目标

xmg-kb 是知识库基础设施，不是业务 Agent 平台。

它负责把异构 Evidence 转化为：

1. 人类长期维护的 Canonical Wiki；
2. 面向 AI/应用的高质量 RAG Index；
3. 稳定的 Knowledge API / Retrieval API / MCP。

系统永久分离：

```text
Evidence
Canonical Knowledge
RAG Chunks
External Consumers
```

外部 Agent、聊天机器人和业务系统只消费接口，不进入 xmg-kb 内部生命周期。

## 2. 七层架构

```text
┌──────────────────────────────────────┐
│ 7. Interface                         │
│ REST API / MCP                       │
├──────────────────────────────────────┤
│ 6. Retrieval                         │
│ RAGFlow / Hybrid / Rerank            │
├──────────────────────────────────────┤
│ 5. Canonical Knowledge               │
│ BookStack / Review / History         │
├──────────────────────────────────────┤
│ 4. Knowledge Governance              │
│ KU / Version / Conflict / Canonical  │
├──────────────────────────────────────┤
│ 3. Document Governance               │
│ Dedup / Metadata / Taxonomy          │
├──────────────────────────────────────┤
│ 2. Ingestion                         │
│ Prefect / Docling Serve / MinerU     │
├──────────────────────────────────────┤
│ 1. Evidence                          │
│ Raw / Legacy / External Sources      │
└──────────────────────────────────────┘
```

横向公共能力：

```text
State
Provenance
Security
Audit
Observability
Backup / Restore
Config
Adapter Registry
```

## 3. 总体数据流

```text
Evidence Sources
  ├─ Markdown / HTML
  ├─ PDF / Image
  ├─ DOCX / PPTX / XLSX
  └─ Historical Curated Knowledge
          ↓
Source Registry / Manifest
          ↓
Prefect
  ├─ Retry
  ├─ Cache
  ├─ Resume
  ├─ Schedule
  └─ Concurrency
          ↓
Document Parsing
  ├─ Docling Serve
  └─ MinerU fallback
          ↓
Normalized Evidence
  ├─ Structured Data
  ├─ Markdown
  ├─ Assets
  └─ Provenance
          ↓
Document Governance
  ├─ Exact Dedup
  ├─ Near-document Dedup
  ├─ Metadata / Taxonomy / Alias
  ├─ Version
  ├─ Authority
  └─ Security Classification
          ↓
Knowledge Governance
  ├─ Section
  ├─ Knowledge Unit
  ├─ Relation
  ├─ Conflict
  └─ Canonicalization
          ↓
BookStack Review
          ↓
Human Approval
          ↓
BookStack Canonical Wiki
        ├──────────────────────────────┐
        ↓                              ↓
Knowledge API / MCP          Canonical-only Sync
                                       ↓
                                    RAGFlow
                              ├─ Parser
                              ├─ Chunker
                              ├─ Transformer（可选）
                              └─ Indexer
                                       ↓
                         Metadata / Hybrid / Rerank
                                       ↓
                                Retrieval API / MCP
                                       ↓
                             External Applications
```

Langfuse 横向记录 Retrieval/QA Trace、Feedback 和 Evaluation；Knowledge Evolution 只产生 Review Proposal，不直接覆盖 Canonical。

## 4. Human Wiki：BookStack

BookStack 是当前默认 Canonical Wiki 实现。

选择目标：

- Self-hosted；
- 人类直接 Web 阅读与编辑；
- WYSIWYG/Markdown 能力；
- 层级、搜索、附件、历史、权限；
- REST API；
- Webhook/事件能力；
- Backup/Restore；
- 运行维护简单。

架构上不允许业务逻辑直接依赖 BookStack 数据库。统一通过：

```text
WikiAdapter
    └─ BookStackAdapter
```

未来替换 Wiki 只能新增 Adapter/ADR，不修改知识治理核心模型。

AI 默认通过 xmg-kb API/MCP 操作 Review 内容，不直接绕过审核修改关键 Canonical 技术事实。

## 5. Workflow：Prefect

Prefect 只负责确定性的 Task Lifecycle：

- Flow / Task；
- Retry；
- Cache；
- Schedule；
- Result Persistence；
- Concurrency；
- Durable State；
- Worker。

业务判断放在 Policy；组件执行放在 Adapter。

推荐关系：

```text
Prefect Flow
    ↓
Policy
    ↓
Adapter
    ↓
Upstream Component
```

xmg-kb 不实现第二套 Workflow Runtime。

## 6. Parser：Docling Serve + MinerU

Docling Serve 是主 Parser，使用异步任务模式：

```text
submit
→ task_id
→ poll
→ quality gate
→ result
```

MinerU 只处理 Docling 未通过 Parse Quality Gate 的复杂文档。

Parser 输出必须保留：

- Structured representation；
- Markdown；
- Assets；
- Parser Version；
- Source Hash；
- Provenance。

Legacy Office 可先经 LibreOffice 标准化；ClamAV 仅负责扫描，不修改 Evidence。

## 7. Document Governance

三层治理：

### Level 1：Exact File

```text
SHA256
```

### Level 2：Near Document

候选信号：Filename、Title、Heading Tree、MinHash、Normalized Text、Embedding、Version。

### Level 3：Knowledge-level

在 Knowledge Unit 上判断：

- `equivalent`
- `supplements`
- `supersedes`
- `version_specific`
- `conflicts`
- `example_of`
- `unrelated`

## 8. Knowledge Unit

永久保持：

```text
Knowledge Unit
= 治理单位
= 去重 / 版本 / 冲突 / Canonical

RAG Chunk
= 检索单位
= Retrieval Context
```

不能用 RAG Chunk 替代知识治理模型。

## 9. Knowledge Engineering

MVP 采用薄 Simple Curator：

```text
Section
→ Schema-constrained KU Extraction
→ Candidate Search
→ Relation Judgment
→ Cluster / Conflict
→ Canonical Proposal
```

OpenSPG/KAG 仅作为同数据集 POC；只有真实 Benchmark 明显改善 KU Accuracy、Alignment、Conflict Discovery 或 Canonical Quality，且运维成本可接受时才 ADOPT。

## 10. Canonicalization

允许动作：

- `CREATE`
- `PATCH`
- `SUPPLEMENT`
- `SUPERSEDE`
- `CONFLICT_REVIEW`
- `NO_ACTION`

禁止 `AUTO_DELETE`。

已有主题优先 `PATCH > CREATE`，目标是知识收敛而不是页面无限增长。

## 11. Production RAG：RAGFlow

Production 只索引：

```text
BookStack Canonical
```

禁止：

- Raw → Production；
- Legacy → Production；
- Review → Production；
- Normalized → Production。

正式流程：

```text
Canonical Page
→ Parser
→ Chunker
→ optional Transformer
→ Indexer
→ Metadata Filter
→ Hybrid Retrieval
→ Rerank
```

xmg-kb 只控制同步、Revision、Metadata、Dataset、检索参数和质量，不自研第二套 Chunk Engine、Vector DB 或 Hybrid Search Engine。

## 12. Chunking 与 Metadata

技术文档优先 Benchmark：

```text
Heading-aware + Token Control
```

保护 Code Block、Table、Procedure、Version Section。

Chunk Size 不写死，由 Gold QA Benchmark 决定。

每个 Production Chunk 至少继承：

```text
wiki_page_id
wiki_revision
canonical_id
heading_path
vendor
product
component
version
category
authority
content_sha256
```

无法回溯 Canonical Page + Revision 的 Chunk 无效。

## 13. Incremental Sync

```text
Revision N → N+1
```

同步必须：

```text
detect revision/hash
→ ingest N+1
→ index ready
→ validate
→ activate N+1
→ retire N
```

失败时继续保留 N，避免新旧两个 Revision 同时有效。

## 14. API

xmg-kb 自身提供稳定逻辑接口，而不是让外部项目直接耦合 Wiki/RAGFlow 内部实现。

### Knowledge API

```text
search/read canonical
source/provenance lookup
history
create/patch review
comment
```

### Retrieval API

```text
search
retrieve
context
metadata filter
citation
canonical/page/revision traceability
```

具体 URL/协议可在实现阶段版本化，但接口语义应稳定。

## 15. MCP

MCP 是 xmg-kb API/Adapter 的 AI 标准入口，不重新实现另一套知识逻辑。

默认 Tools：

```text
knowledge_search
knowledge_read
knowledge_sources
rag_search
rag_context
review_create
review_patch
review_comment
```

默认禁用 Canonical Delete、强制覆盖和索引销毁等高风险 Tool。

## 16. Langfuse / Knowledge Evolution

Langfuse 记录 Query、Retrieval Context、Canonical IDs、Answer、Citation、Latency、Feedback、Dataset 与 Evaluation。

使用信号可分类为：

- `GOOD`
- `WEAK`
- `MISSING`
- `CONFLICT`
- `OUTDATED`
- `FRAGMENTED`

这些信号只能形成 Review Proposal，不能直接修改 Canonical。

## 17. Adapter / Harness 原则

核心逻辑只依赖稳定接口：

```text
SourceAdapter
ParserAdapter
WikiAdapter
RagAdapter
ObservabilityAdapter
```

新增或替换组件优先通过 Adapter/Registry 完成，不修改核心知识模型和 Flow 语义。

## 18. Packaging

仓库只提供薄封装，不 fork 上游产品。

建议：

```text
deploy/
  bookstack/
  prefect/
  docling-serve/
  mineru/
  ragflow/
  langfuse/
  kag-poc/

src/xmg_kb/
  adapters/
  flows/
  policies/
  schemas/
  api/
  mcp/

config/examples/
scripts/
tests/
```

统一生命周期命令建议：

```text
bootstrap
up-core
up-ingestion
up-rag
up-observability
status
verify
test
backup
restore
```

## 19. 非目标

xmg-kb 不负责：

- 具体业务 Agent；
- Multi-Agent Runtime；
- Chat/IM Bot；
- Ticket/工单系统；
- DingTalk/Slack 等业务入口；
- 自动运维执行。

也不自研：Wiki Editor、OCR/PDF Layout Engine、Workflow Runtime、Vector Database、Search Engine、Trace Platform、Evaluation Dashboard、通用 Graph DB、通用 MCP 协议框架。