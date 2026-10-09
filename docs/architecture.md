# 总体架构

## 1. 架构目标

xmg-kb 是文件型企业知识库生产与治理基础设施，不是业务 Agent 平台，也不在当前阶段建设 Wiki UI。

核心原则：

- **文件系统是 Canonical Knowledge**：Markdown、HTML、图片、视频、PDF 和其他附件真实存储在本地知识目录。
- **应用必须操作原文件**：未来展示/编辑层须原生读写这些文件，不得把 Wiki 数据库作为第二份知识事实源。
- **GitLab 是后续同步/备份目标**：不是当前运行依赖，也不是知识本体。
- **RAG 是派生索引**：可以删除重建，不能成为唯一内容来源。
- **原始 Evidence 不可变**：处理结果写入独立工作区和知识目录，保留来源链路。

## 2. 文件型知识库生产管线

```text
Sources: local folders / network / web / API / Office / PDF / images / human / agents
                                  ↓
                        Source Adapter + Manifest
                                  ↓
                 Inventory / Hash / Reuse / Dedup
                                  ↓
                     Parser Adapter + Fallback
                                  ↓
                   Normalize: Markdown + Assets
                                  ↓
           Knowledge Build: Classify / Split / Merge / Link
                                  ↓
                   Local File Knowledge Store
                                  ↓
             Directory / Quality / Provenance Governance
                                  ↓
                         Knowledge API / MCP
                                  ↓
                         RAGFlow Derived Index
                                  ↓
                         External Agents
                                  ↓
                    Feedback / Evidence / Proposal
                                  └────────→ Knowledge Build
```

## 3. 本地知识目录边界

运行目录与代码仓库分离，通过配置指定实际路径。公开示例：

```text
/srv/xmg-kb/
├── sources/       # 来源清单和只读引用
├── work/          # 临时解析和转换结果，可重建
├── knowledge/     # Canonical Markdown/HTML/assets
├── metadata/      # provenance、hash、分类、质量与变更映射
├── state/         # checkpoint、任务状态、重试状态
├── quarantine/    # 失败、损坏或待人工处理内容
└── logs/          # 运行日志
```

## 4. 文件与元数据模型

Markdown 是主要结构化知识格式；必要时保留 HTML；图片、图表、视频、音频和附件以独立文件保存。来源、hash、解析器版本、置信度、权限、版本范围等元数据与正文分离。每份 Canonical Knowledge 必须追溯到来源；移动或重命名文件时检查内部链接和资产引用。Knowledge Unit 用于治理，RAG Chunk 用于检索，两者不能混用。

## 5. 目录治理

目录树是持续治理对象。系统识别重复/重叠目录、孤儿文件、过深层级、主题混杂、断链和命名不一致，并生成变更提案。目录迁移必须 dry-run、链接检查、差异预览、审计和回滚；高影响变更需人工批准。

## 6. Agent 反馈闭环

外部 Agent 可提交使用信号、缺失问题、新证据和建议修订。反馈先形成带来源、任务 ID、证据、影响范围和置信度的 Proposal，再按策略进入自动低风险修订、人工审核或隔离队列。聊天回答本身不能自动视为事实证据。

## 7. 当前组件边界

- Prefect：任务生命周期、重试、恢复和并发。
- Docling Serve：默认解析器；MinerU/OCR/LibreOffice 按格式与质量触发。
- 本地文件系统：唯一 Canonical Knowledge Store。
- RAGFlow：派生索引与检索。
- xmg-kb API/MCP：受控读取、来源查询、提案和反馈。
- GitLab：未来双向同步/备份适配器，当前不部署、不构成依赖。
- Wiki UI：暂缓；未来候选必须直接操作本地文件，并通过 POC 验证。

## 8. Workflow：Prefect

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