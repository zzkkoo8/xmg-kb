# 历史设计审计与最终收敛

本文用于解释 xmg-kb 为什么形成当前架构。它只保留可以公开的架构结论，不包含任何真实知识内容、私有目录、运行状态或内部审计数据。

## 1. 历史设计演进

### v3：从“文档处理”升级为“知识治理”

关键贡献：

- 明确 Knowledge Unit；
- 三层去重：Exact File、Near Document、Knowledge-level Semantic；
- Version Scope；
- Authority；
- Conflict != Duplicate；
- Canonical Synthesis；
- Provenance；
- KAG / GraphRAG 等方案评估。

保留结论：

> 文档去重不能解决“同一知识点散落在多份资料”的问题，必须增加知识级治理层。

### v4：形成 Wiki + RAG + Workflow + Feedback 主骨架

关键贡献：

- Human Wiki 与 Production RAG 分层；
- Prefect 负责 Workflow；
- Docling/MinerU 负责解析；
- RAGFlow 负责正式检索；
- Langfuse 负责真实使用反馈；
- KAG 变为可选 Knowledge Engineering POC；
- Knowledge Evolution Loop。

保留结论：

> 不自研基础设施，使用成熟组件拼接，领域代码只做治理和适配。

### v5：明确 Review / Canonical 生命周期

关键贡献：

- Draft / Review / Canonical 分层；
- AI 默认写 Review；
- Human Approval；
- Wiki 变更触发 RAG 增量同步；
- Canonical State 与机器状态一致性。

保留结论：

> AI 可以编辑，但不能绕过审核直接覆盖正式技术事实。

### v6：明确 Evidence Pipeline 与 RAG Pipeline 是两件事

关键贡献：

```text
Evidence Pipeline:
Raw/Legacy
→ Parse
→ Governance
→ Canonical

RAG Pipeline:
Canonical
→ Chunk
→ Index
→ Retrieve
```

保留结论：

> RAG Chunking 必须发生在 Canonical 之后，不能用“Raw 全量切片”替代知识治理。

### v7：把架构升级为 Execution-Ready Gate

关键贡献：

- Bootstrap；
- Prerequisites；
- Preflight；
- Acceptance；
- Stop Conditions；
- Rollback；
- Phase Gate；
- Legacy Reuse；
- Source of Truth；
- Backup / Restore。

保留结论：

> “代码存在”“Compose 存在”“旧报告写 PASS”都不是完成证据，必须由实际 Health/Test/API/Data Evidence 验收。

## 2. 历史实施计划审计得到的工程教训

对历史 Phase 计划和进度文档复核后，保留以下通用工程原则。

### 2.1 Gate 不能只写在文档里

必须让：

```text
Prerequisites
→ Runtime Evidence
→ Acceptance
```

真正决定下一 Phase 是否可运行。

### 2.2 旧资产优先复用

如果已有高质量解析/整理成果：

```text
Reuse
```

优先于：

```text
Reparse / Re-LLM
```

但复用必须保留 Source Mapping 和 Provenance。

### 2.3 旧实现不自动等于最终架构 PASS

历史代码或数据可以：

- Reuse；
- Adapt；
- Migrate；

但如果产生于最终 Gate 之前，只能算“已有资产”，不能直接跳过最终验收。

### 2.4 Runtime 与公共代码必须彻底分离

真实 Knowledge、State、Logs、Trace、Database、Report 均应在 Git checkout 外运行。

公共仓库只保存：Code、Public Docs、Config Template、Synthetic Fixture。

## 3. 最终架构调整：Human Wiki

早期方案默认 Outline。

重新以“成熟 + 自托管 + 开源 + 稳定 API + AI 可读写 + 易分发”审计后，当前公开基线改为 BookStack：

- MIT；
- REST API；
- Markdown + WYSIWYG；
- Hierarchy；
- History；
- Attachment；
- Permission；
- Webhook；
- Import/Export。

Outline 保留为 Source-Available Alternative，不作为默认开源 Profile。

## 4. 最终不变的核心原则

```text
Evidence != Canonical
Knowledge Unit != RAG Chunk
Canonical Wiki != RAG Index
AI Draft != Approved Knowledge
Deployment != Verified
Code Exists != PASS
```

## 5. 当前公共架构基线

```text
BookStack
+
Prefect
+
Docling Serve
+
MinerU fallback
+
RAGFlow
+
Langfuse
+
Simple Curator
+
KAG POC
```

自定义代码只做：

```text
Adapter
Schema
Policy
Prompt
Flow
Mapping
Sync
MCP Safety Layer
Test
```

## 6. 何时允许改变基线

任何替换核心组件的提议都必须新增 ADR，并至少回答：

1. 当前组件哪里实测不满足需求；
2. 新组件是否更成熟；
3. License 是否更适合；
4. API 是否稳定；
5. 迁移成本；
6. Data Portability；
7. Benchmark；
8. Rollback。

没有这些证据，不允许因“更流行”或“感觉更先进”替换主链。
