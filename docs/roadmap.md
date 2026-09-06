# v7 研发路线图

本路线图是当前公开的 v7 Phase Gate 摘要。每个 Phase 必须满足前置条件，并以测试、API、运行状态、数据指标或可复现命令作为验收证据；目录、代码、Compose 或历史报告存在都不等于 `PASS`。

状态只允许：`NOT_STARTED`、`IN_PROGRESS`、`IMPLEMENTED_UNVERIFIED`、`PASS`、`BLOCKED`、`DEVIATED`。

## Phase 0 — Baseline + Resource Preflight

固定工程边界、资源、存储、端口和 Source of Truth 合同，并证明检查过程未修改 Evidence Source。

## Phase 1 — Bootstrap All Components

锁定并验证 Outline、Prefect、Docling Serve、MinerU、RAGFlow、Langfuse、LibreOffice、ClamAV 与可选 KAG POC。验收至少覆盖版本/镜像摘要、API/健康、持久化、重启和默认凭据处置；不得在本阶段导入正式知识。

## Phase 2 — Full Source Inventory

为 Raw Evidence 与 Legacy Curated Source 建立全量 Manifest、稳定 Source ID、SHA-256、格式、状态与 Provenance；支持增量重跑，不修改源文件。

## Phase 3 — Legacy Reuse Mapping

优先复用高质量 Legacy，明确 Accepted、Needs Repair、Duplicate、Legacy-only、Unmapped、Unsupported 与 Quarantined 等最终状态，并建立 Raw → Legacy → 新治理层的可解释映射。

## Phase 4 — Selective Parsing Pilot

用代表性小样本验证 Prefect → Docling Serve Async → Parse Quality → MinerU fallback → Normalize；验证重试、恢复、失败隔离、版本与 Provenance。

## Phase 5 — Bulk Parsing Runtime

验证有界队列、并发、缓存、幂等、Worker 重启与单文档重试，再逐批扩大处理规模；不得以无状态脚本代替正式 Runtime。

## Phase 6 — Document Governance

建立 Exact/Near Dedup、Metadata、Taxonomy、Alias、Version、Authority 与 Security Classification。关键错误合并为零，覆盖率与精度达到设计阈值。

## Phase 7 — Outline Information Architecture POC

验证 Collection、层级、编辑、搜索、附件、评论、历史、权限、API/MCP、导入导出及备份恢复，并由 Human Owner 明确批准 IA。

## Phase 8 — Knowledge Engineering POC

在同一数据集上比较 Simple Curator 与 KAG/OpenSPG，形成 Knowledge Unit、Relation、Cluster、Conflict 和 Canonical Draft；KAG 只有证明真实收益后才 `ADOPT`。

## Phase 9 — Canonicalization Policy

实现并验证 `CREATE`、`PATCH`、`SUPPLEMENT`、`SUPERSEDE`、`CONFLICT_REVIEW` 等收敛策略、模板、来源追踪和版本规则。

## Phase 10 — Review → Canonical Wiki Pilot

让候选内容先进入 Outline Review，经人工审批后进入 Canonical Collections；验证 Webhook 签名、重放保护、幂等、乱序处理和 Outline Mapping。

## Phase 11 — Source of Truth Cutover

把 Outline Canonical Collections 切为唯一人类知识事实源，停止平行 Canonical 写入，验证 API/MCP、Mapping、导出与备份。

## Phase 12 — RAGFlow Production Pipeline

仅从 Outline Canonical 执行 Parser → Chunker → optional Transformer → Indexer；Chunk 继承 Canonical/Revision 元数据，增量同步幂等且失败时保留上一有效 Revision。

## Phase 13 — Chunk / Retrieval Benchmark

建立 Gold QA，比较 Full-text、Vector、Hybrid、Hybrid + Rerank 及多种结构/Chunk 参数；以 Recall、Citation、Faithfulness、Refusal 和 Critical Hallucination 验收。

## Phase 14 — xmg-qa Integration

让问答系统只通过正式 RAGFlow 检索链读取 Canonical 派生索引，Citation 可回到 Outline；消除对 Raw、Legacy 和旧索引的运行时依赖。

## Phase 15 — AI Knowledge Management

通过受控 Outline API/MCP 提供 Search、Read、Create/Patch Review、Comment 和 Source Lookup；默认禁止删除 Canonical、绕过 Review 与静默解决冲突。

## Phase 16 — Langfuse Observability

接入 Query、Retrieval、Canonical IDs、Chunks、Answer、Citation、Latency、Feedback、Score、Dataset 与 Evaluation，同时保护敏感正文。

## Phase 17 — Knowledge Evolution Loop

从真实使用识别 `GOOD`、`WEAK`、`MISSING`、`CONFLICT`、`OUTDATED`、`FRAGMENTED`，生成带证据和优先级的 Review Proposal，不直接改写 Canonical。

## Phase 18 — Three-Product Scale Test

选择三个质量和结构不同的产品域，证明同一套代码可复用，差异只进入 Taxonomy、Alias、Policy 和 Prompt，而不是产生平行 Pipeline。

## Phase 19 — Full 70GB Migration

按产品/领域分批完成全量迁移；每个 Source 有最终状态，失败可恢复，缓存避免重复昂贵处理，并持续输出可审计进度。

## Phase 20 — Legacy Retirement Gate

只有全量迁移、Outline Canonical、RAGFlow、xmg-qa、Gold QA、最终备份与 Restore 全部通过，且 Legacy 运行时依赖为零，才允许生成 Retirement Ready 结论。

## Phase 21 — Optional Legacy Deletion

这是独立、显式授权的可选破坏性阶段。必须在 Phase 20 `PASS` 后再次确认精确路径、归档/备份和用户批准；默认不执行。

## Phase 22 — Backup / Restore / Hardening

完成各组件与治理状态的备份、恢复演练、故障注入、安全加固、升级/回滚和运维验收。只有实际 Restore Drill 成功，备份才有效。

## Gate 纪律

- 从 Phase 0 向后寻找最早未通过的 Gate；前置未通过时不得把后续资产标成 `PASS`。
- Historical PASS 与当前实测冲突时，以当前实测为准。
- Production RAG 只接受 Outline Canonical，不得混入 Raw、Legacy、Review 或 Archive。
- 真实知识、状态库、索引、日志、Trace、备份和内部报告不得进入公共 Git。
