# 总体架构

## 1. 架构目标

xmg-kb 将异构 Evidence 转化为两个稳定产物：

1. 人类长期维护的 Canonical Wiki；
2. 面向 AI QA 的高质量 RAG Index。

系统明确分离：

```text
Evidence
Canonical Knowledge
RAG Chunks
```

三者不能混为一层。

## 2. 总体流程

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
  ├─ Structured JSON
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
  ├─ Relations
  ├─ Conflict
  └─ Canonicalization
          ↓
Outline 90-Review
          ↓
Human Approval
          ↓
Outline Canonical Collections
        ├─────────────────────────┐
        ↓                         ↓
Outline API/MCP + Webhook   Canonical-only Sync
        ↓                         ↓
Knowledge-management AI       RAGFlow
                              ├─ Parser
                              ├─ Chunker
                              ├─ Transformer（可选）
                              └─ Indexer
                                   ↓
                    Metadata Filter / Hybrid / Rerank
                                   ↓
                                  QA AI
                                   ↓
                               Langfuse
                                   ↓
                  Knowledge Evolution Candidates
                                   ↓
                              Review Queue
```

## 3. Human Wiki：Outline

Outline 作为 v7 默认 Canonical Wiki。

选择理由：

- MIT；
- 自托管；
- WYSIWYG；
- Markdown；
- Books / Chapters / Pages；
- Search；
- Tags；
- Attachments；
- Page History；
- Permissions；
- Webhooks；
- 内置 REST API；
- Export / Import；
- 运维和备份文档成熟。

AI 不直接操作 Outline 数据库。

自动化统一使用：

```text
Outline API / MCP
```

标准 Agent 接口通过一个薄的 `xmgkb-mcp` 适配层暴露。

默认工具：

```text
wiki_search
wiki_read
wiki_sources
wiki_create_review
wiki_patch_review
wiki_comment
rag_search
```

破坏性 Canonical 操作默认不开放。

## 4. Workflow：Prefect

Prefect 负责：

- Flow / Task；
- Retry；
- Cache；
- Schedule；
- Result Persistence；
- Concurrency；
- Durable State；
- Worker。

xmg-kb 不实现第二套 Workflow Runtime。

## 5. Parser：Docling Serve + MinerU

Docling Serve 是主 Parser，使用异步任务接口：

```text
submit
→ task_id
→ poll
→ result
```

MinerU 只处理 Docling 未通过 Parse Quality Gate 的复杂文档。

Parser 输出保留：

- 结构化数据；
- Markdown；
- Assets；
- Parser Version；
- Source Hash；
- Provenance。

## 6. Document Governance

### Level 1：Exact File

```text
SHA256
```

### Level 2：Near Document

候选信号：

- Filename；
- Title；
- Heading Tree；
- MinHash；
- Normalized Text；
- Embedding；
- Version。

### Level 3：Knowledge-level

在 Knowledge Unit 上判断：

- `equivalent`
- `supplements`
- `supersedes`
- `version_specific`
- `conflicts`
- `example_of`
- `unrelated`

## 7. Knowledge Unit

Knowledge Unit 是治理单位，不是 RAG Chunk。

```text
Knowledge Unit
= 去重 / 版本 / 冲突 / Canonical

RAG Chunk
= Retrieval
```

## 8. Knowledge Engineering

默认实现一个薄的 Simple Curator：

```text
Section
→ Schema-constrained KU Extraction
→ Candidate Search
→ Relation Judgment
→ Cluster
→ Canonical Proposal
```

OpenSPG/KAG 在同一数据集上 POC。

只有显著提升：

- KU Accuracy；
- Alignment；
- Conflict Discovery；
- Canonical Quality；

且运维成本可接受时才 ADOPT。

## 9. Canonicalization

动作固定为：

- `CREATE`
- `PATCH`
- `SUPPLEMENT`
- `SUPERSEDE`
- `CONFLICT_REVIEW`
- `NO_ACTION`

禁止 `AUTO_DELETE`。

已有主题优先：

```text
PATCH > CREATE
```

目标是知识收敛，而不是页面无限增长。

## 10. Production RAG：RAGFlow

Production 只索引：

```text
Outline Canonical
```

禁止：

- Raw → Production；
- Review → Production；
- Normalized → Production；
- 历史临时语料 → Production。

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

RAGFlow 官方当前 Ingestion Pipeline 本身提供 Parser、Transformer、Chunker、Indexer，因此 xmg-kb 不自研 Chunk Engine。

## 11. Chunking

技术文档优先测试：

```text
Heading-aware
+
Token Control
```

保护：

- Code Block；
- Table；
- Procedure；
- Version Section。

Chunk Size 不能写死，应由 Gold QA Benchmark 决定。

## 12. Chunk Metadata

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

任何无法回溯 Canonical Page 的 Chunk 都是无效数据。

## 13. Incremental Sync

Wiki Revision：

```text
N → N+1
```

同步：

```text
detect hash/revision
→ ingest N+1
→ index ready
→ validate
→ activate N+1
→ retire N
```

失败则保留 N。

## 14. Langfuse

Langfuse 负责：

- Trace；
- Retrieval Context；
- Answer；
- Feedback；
- Dataset；
- Evaluation；
- Experiment。

它只产生 Evolution Signal，不直接修改 Canonical。

## 15. Knowledge Evolution

状态：

- `GOOD`
- `WEAK`
- `MISSING`
- `CONFLICT`
- `OUTDATED`
- `FRAGMENTED`

高优先级事件：

```text
Evidence Search
→ CREATE / PATCH / CONFLICT_REVIEW
→ Outline 90-Review
→ Human Approval
```

## 16. Packaging

仓库提供薄封装，不 fork 上游产品。

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
  mcp/

config/examples/
scripts/
tests/
```

生命周期命令建议统一为：

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

## 17. 非目标

不自研：

- Wiki Editor；
- OCR；
- PDF Layout Engine；
- Workflow Runtime；
- Vector Database；
- Search Engine；
- Trace Platform；
- Evaluation Dashboard；
- 通用 Graph DB；
- 通用 MCP 协议框架。
