# v7 研发路线图（知识平台边界版）

本路线图保留现有 Phase 编号，避免破坏历史报告和当前开发进度；但项目边界已收敛为：**Ingestion + Governance + Wiki + RAG + API + MCP + Operations**。

业务 Agent、聊天机器人、工单、钉钉和 Multi-Agent 不属于 xmg-kb，也不得成为任何 Phase Gate。

状态只允许：`NOT_STARTED`、`IN_PROGRESS`、`IMPLEMENTED_UNVERIFIED`、`PASS`、`BLOCKED`、`DEVIATED`。

## Phase 0 — Baseline + Resource Preflight

固定工程边界、资源、存储、端口、Source of Truth 和公共/私有数据边界；证明检查过程未修改 Evidence Source。

## Phase 1 — Bootstrap Core Components

锁定并验证 BookStack、Prefect、Docling Serve、MinerU、RAGFlow、LibreOffice、ClamAV；Langfuse 可同时部署，但不得因 Observability 尚未接入而阻塞知识主链；KAG/OpenSPG 仅 Optional POC。

验收至少覆盖版本/镜像摘要、API/健康、持久化、重启和默认凭据处置；不得在本阶段导入正式知识。

## Phase 2 — Full Source Inventory

为 Raw Evidence 与 Legacy Curated Source 建立全量 Manifest、稳定 Source ID、SHA-256、格式、状态与 Provenance；支持增量重跑，不修改源文件。

## Phase 3 — Legacy Reuse Mapping

优先复用高质量 Legacy，明确 Accepted、Needs Repair、Duplicate、Archive-only、Unmapped、Unsupported 与 Quarantined 等状态，并建立 Raw → Legacy → 新治理层的可解释映射。

## Phase 4 — Selective Parsing Pilot

用代表性小样本验证 Prefect → Docling Serve Async → Parse Quality → MinerU fallback → Normalize；验证 Retry、Resume、Failure Isolation、Version 与 Provenance。

## Phase 5 — Bulk Parsing Runtime

验证有界队列、并发、缓存、幂等、Worker 重启与单文档重试，再逐批扩大处理规模；不得以无状态脚本代替正式 Runtime。

## Phase 6 — Document Governance

建立 Exact/Near Dedup、Metadata、Taxonomy、Alias、Version、Authority、Security Classification 与 Provenance。关键错误合并为零，覆盖率与精度达到设计阈值。

## Phase 7 — BookStack Human Wiki POC

验证层级、编辑、搜索、附件、评论、历史、权限、REST API、Webhook/事件、Import/Export 与 Backup/Restore，并由 Human Owner 明确批准日常维护体验。

## Phase 8 — Knowledge Engineering POC

在同一数据集上验证 Simple Curator，形成 Knowledge Unit、Relation、Cluster、Conflict 与 Canonical Draft；KAG/OpenSPG 仅做对照实验，证明真实收益后才 `ADOPT`。

## Phase 9 — Canonicalization Policy

实现并验证 `CREATE`、`PATCH`、`SUPPLEMENT`、`SUPERSEDE`、`CONFLICT_REVIEW`、`NO_ACTION`，以及来源追踪、Version Scope 与模板规则。禁止 `AUTO_DELETE`。

## Phase 10 — Review → Canonical Wiki Pilot

候选内容先进入 BookStack Review 区，经人工审批后进入 Canonical；验证 API、Mapping、Revision、Webhook/事件、幂等和乱序处理。

## Phase 11 — Source of Truth Cutover

把 BookStack Canonical 切为唯一人类知识事实源，停止平行 Canonical 写入，验证 Mapping、Export、Backup/Restore 和 WikiAdapter。

## Phase 12 — RAGFlow Production Pipeline

仅从 BookStack Canonical 执行 Parser → Chunker → optional Transformer → Indexer；Chunk 继承 Canonical/Page/Revision 元数据，增量同步幂等且失败时保留上一有效 Revision。

## Phase 13 — Chunk / Retrieval Benchmark

建立 Gold QA，比较 Full-text、Vector、Hybrid、Hybrid + Rerank 及多种结构/Chunk 参数；以 Recall、Citation、Faithfulness、Refusal 和 Critical Hallucination 验收。

## Phase 14 — Knowledge / Retrieval API

建立 xmg-kb 自身的稳定接口契约，避免外部系统直接耦合 BookStack 或 RAGFlow 内部 API。

至少验证：

- Canonical Search / Read；
- Provenance / Source Lookup；
- Retrieval / Context；
- Metadata Filter；
- Citation；
- Canonical/Page/Revision Traceability；
- API Versioning / Error Contract；
- Auth / Permission Boundary。

本 Phase 不集成任何具体业务 Agent。

## Phase 15 — MCP / AI Knowledge Management

通过 xmg-kb API/Adapter 暴露受控 MCP Tools：Search、Read、Source Lookup、RAG Search/Context、Create/Patch Review、Comment。

默认禁止 Canonical Delete、绕过 Review、强制覆盖和静默解决 Conflict。

## Phase 16 — Langfuse Observability

接入 Query、Retrieval、Canonical IDs、Chunks、Answer、Citation、Latency、Feedback、Score、Dataset 与 Evaluation；保护敏感正文，Observability 不成为知识事实源。

## Phase 17 — Knowledge Evolution Loop

从真实使用信号识别 `GOOD`、`WEAK`、`MISSING`、`CONFLICT`、`OUTDATED`、`FRAGMENTED`，生成带证据和优先级的 Review Proposal，不直接改写 Canonical。

## Phase 18 — Multi-domain Scale Test

选择多个质量和结构不同的知识域，证明同一套代码可复用，差异主要进入 Taxonomy、Alias、Policy 和 Prompt，而不是产生平行 Pipeline。

## Phase 19 — Full Migration

按产品/领域分批完成全量迁移；每个 Source 有最终状态，失败可恢复，缓存避免重复昂贵处理，并持续输出可审计进度。

## Phase 20 — Legacy Retirement Gate

只有全量迁移、Canonical Wiki、RAGFlow Production、API/MCP、Gold QA、最终 Backup 与 Restore 全部通过，且 Legacy 运行时依赖为零，才允许生成 `RETIREMENT_READY` 结论。

不要求任何外部业务 Agent 完成迁移后才能通过本 Gate。

## Phase 21 — Optional Legacy Archive / Removal

独立、显式授权的可选破坏性阶段。必须在 Phase 20 `PASS` 后再次确认精确路径、归档/备份、恢复能力和用户批准；默认不执行删除。

## Phase 22 — Backup / Restore / Hardening

完成各组件与治理状态的 Backup、Restore Drill、故障注入、安全加固、升级/回滚和运维验收。只有实际 Restore Drill 成功，备份才有效。

## 对外展示的 8 个 Stage

为了降低 README/产品理解复杂度，对外可归纳为：

```text
Stage 0  Foundation
Stage 1  Ingestion
Stage 2  Document Governance
Stage 3  Knowledge Governance
Stage 4  Canonical Wiki
Stage 5  RAG
Stage 6  API / MCP
Stage 7  Operations / Evolution
```

内部仍使用 Phase 0–22 保持可审计 Gate。

## Gate 纪律

- 从 Phase 0 向后寻找最早未通过的 Gate；前置未通过时不得把后续资产直接标成 `PASS`。
- Historical PASS 与当前实测冲突时，以当前实测为准。
- 已存在的后续资产标记为 `PRE_EXISTING_REUSABLE_ASSET`，优先复用，不因 `DEVIATED` 自动重做。
- Production RAG 只接受 BookStack Canonical，不得混入 Raw、Legacy、Review 或 Normalized。
- 外部业务 Agent 不是 xmg-kb Phase Gate。
- 真实知识、状态库、索引、日志、Trace、备份和内部报告不得进入公共 Git。