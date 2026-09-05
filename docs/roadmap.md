# 研发路线图

所有阶段均采用 Gate 模式。

后续 Phase 只有在前置 Phase 有真实验收证据后才能启用。

## Phase 0 — Preflight

目标：

- 主机资源；
- 存储；
- Container Runtime；
- 网络；
- 端口；
- 组件兼容性。

验收：

- Resource Report；
- Storage Headroom；
- Port Plan；
- Runtime Mode；
- 无 Knowledge Data 被修改。

## Phase 1 — Bootstrap Components

部署、锁定版本、Smoke Test：

- BookStack；
- Prefect；
- Docling Serve；
- MinerU；
- RAGFlow；
- Langfuse；
- KAG/OpenSPG POC。

此阶段不得导入正式知识。

验收：

- Exact Version / Digest；
- Service Starts；
- API/UI Health；
- Restart Persistence；
- 默认凭据已处理；
- Production Dataset 为空。

## Phase 2 — Source Registry / Manifest

建立稳定 Source ID、Hash、Metadata、Provenance。

验收：

- Eligible Sources 100% 登记；
- Incremental Rerun；
- Source File 不被修改。

## Phase 3 — Reuse Mapping

已整理内容优先复用。

状态至少：

- Accepted Reuse；
- Needs Repair；
- Confirmed Duplicate；
- Archive Only；
- Unsupported；
- Quarantined；
- Unmapped。

验收：

- 映射规则可解释；
- Accepted 不重复 Parser；
- Unresolved 可查询。

## Phase 4 — Parser Pilot

代表性语料：

```text
Docling Serve
→ Parse Quality Gate
→ MinerU fallback
```

验收：

- Async Submit/Status/Result；
- Retry / Resume；
- 单文档失败隔离；
- Provenance；
- Critical Fact 保留；
- Threshold 由 Pilot 校准。

## Phase 5 — Bulk Ingestion Runtime

建立有界批处理和并发限制。

验收：

- 至少 1,000 个代表性文件 Queue 测试；
- Worker Restart 不丢状态；
- Completed 不重复；
- Storage / Throughput 可量化；
- Fail 可单文档 Retry。

## Phase 6 — Document Governance

执行：

- Exact Dedup；
- Near-document Dedup；
- Metadata；
- Taxonomy / Alias；
- Version；
- Authority；
- Security Classification。

初始验收：

- Exact Precision = 100%；
- Near Duplicate Precision >= 95%；
- Critical Wrong Version Merge = 0；
- Required Metadata Coverage >= 99%。

## Phase 7 — Human Wiki Pilot

验证 BookStack 是否满足长期人类维护。

验收：

- WYSIWYG；
- Markdown；
- Hierarchy；
- Search；
- Tags；
- Attachments；
- Comments；
- History；
- Permissions；
- REST API；
- Backup / Restore；
- Human Owner 明确批准。

## Phase 8 — Knowledge Engineering POC

同一语料比较：

```text
Simple Curator
vs
KAG/OpenSPG
```

初始目标：

- Source Traceability = 100%；
- KU Factual Precision >= 98%；
- Critical Wrong Merge = 0；
- Alignment Precision >= 95%；
- >= 30 Canonical Drafts。

KAG 必须通过真实收益证明才 ADOPT。

## Phase 9 — Canonical Workflow

所有 AI / Pipeline 内容先进入 Review。

批准后进入 Canonical。

验收：

- Source Traceable；
- Version Explicit；
- Unsupported Claim = 0；
- Duplicate Canonical = 0；
- Review Permission 生效。

## Phase 10 — RAG Production Ingestion

```text
Canonical
→ Parser
→ Chunker
→ optional Transformer
→ Indexer
```

验收：

- Production 只有 Canonical；
- Review/Raw 无法检索；
- Chunk 继承 Page/Revision Metadata；
- Incremental Idempotent；
- 新 Revision 失败时旧 Revision 仍可用。

## Phase 11 — Retrieval Benchmark

至少比较：

- Full-text；
- Vector；
- Hybrid；
- Hybrid + Rerank；
- 多个 Chunk Size；
- 多个结构切分策略。

初始目标：

- Top-5 Recall >= 95%；
- Critical Top-5 Recall >= 98%；
- Citation Correctness >= 95%；
- Correct Refusal >= 98%；
- Critical Hallucination = 0。

## Phase 12 — AI Knowledge Management

通过 BookStack REST API + 薄 MCP Adapter 暴露：

- Search；
- Read；
- Create Review；
- Patch Review；
- Comment；
- Source Lookup。

默认禁止：

- Delete Canonical；
- Bypass Review；
- Silent Conflict Resolution。

## Phase 13 — Observability / Eval

Langfuse 接入：

- Query；
- Retrieved Canonical IDs；
- Chunks；
- Answer；
- Citation；
- Latency；
- Feedback；
- Scores。

## Phase 14 — Knowledge Evolution

识别：

- GOOD；
- WEAK；
- MISSING；
- CONFLICT；
- OUTDATED；
- FRAGMENTED。

只生成 Proposal，不直接写 Canonical。

## Phase 15 — Scale Validation

选择多个不同质量领域。

验收：

- 复用同一代码；
- 差异主要落在 Taxonomy / Alias / Policy / Prompt；
- 不产生平行第二套 Pipeline。

## Phase 16 — Full Migration

按 Product/Domain 有界迁移。

验收：

- Every Source Has Final State；
- Unresolved = 0；
- Canonical Traceability = 100%；
- RAG Canonical-only；
- Backup / Restore PASS。

## Phase 17 — Packaging / Distribution

完成：

- Upstream Image Pinning；
- Component Deploy Templates；
- Project CLI/Make；
- Health Check；
- Backup/Restore；
- Upgrade；
- Public Release Safety Gate。

Release 必须能在一个全新环境中，只依靠公开代码和模板完成部署，不依赖任何私有语料。
