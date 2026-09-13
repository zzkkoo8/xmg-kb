# 历史设计审计与最终收敛

本文解释 xmg-kb 的架构演进，只保留可公开的设计结论，不包含真实知识内容、私有目录、运行状态或内部审计数据。

## 1. 历史演进

### v3：从文档处理升级为知识治理

保留：Knowledge Unit、三层去重、Version Scope、Authority、Conflict、Canonical Synthesis、Provenance。

核心结论：文档去重不能解决知识级重复与冲突，必须有 Knowledge Governance。

### v4：形成 Wiki + RAG + Workflow + Feedback 主骨架

保留：Human Wiki 与 Production RAG 分层；Prefect 负责任务生命周期；Docling/MinerU 负责解析；RAGFlow 负责检索；Langfuse 负责质量反馈；KAG 仅做 POC。

核心结论：成熟组件负责基础设施，xmg-kb 只做领域治理和适配。

### v5：明确 Review / Canonical 生命周期

保留：AI 默认写 Review；Human Approval；Canonical Revision 触发 RAG 增量同步。

核心结论：AI 可编辑，但不能绕过审核静默覆盖正式技术事实。

### v6：明确 Evidence Pipeline 与 RAG Pipeline 分离

```text
Evidence Pipeline:
Raw/Legacy → Parse → Governance → Canonical

RAG Pipeline:
Canonical → Chunk → Index → Retrieve
```

核心结论：不能用 Raw 全量切片代替知识治理。

### v7：Execution-Ready Gate

保留：Prerequisites、Preflight、Acceptance、Stop Conditions、Rollback、Phase Gate、Legacy Reuse、Source of Truth、Backup/Restore。

核心结论：代码/Compose/旧报告存在都不是 PASS，必须有当前实测证据。

## 2. 当前最终产品定位

xmg-kb 收敛为：

```text
Knowledge Platform / Knowledge Infrastructure
```

只负责：

```text
Ingestion
Document Governance
Knowledge Governance
Canonical Wiki
RAG
Knowledge / Retrieval API
MCP
Operations / Observability / Backup
```

不负责：业务 Agent、聊天机器人、工单、IM Bot、自动运维、Multi-Agent Runtime。

外部项目只作为 API/MCP/RAG 消费者，不进入 xmg-kb Phase Gate。

## 3. Human Wiki 决策收敛

早期方案使用 Outline 作为默认 Wiki。

在“开源优先、稳定 REST API、人类可维护、AI 可受控读写、易自托管和易分发”的当前约束下，默认基线调整为 BookStack。

架构层面通过 `WikiAdapter` 隔离 Wiki 实现，避免核心治理模型绑定某个产品。

Outline 作为可选替代，不再是默认 Required Component。

## 4. 最终不变的原则

```text
Evidence != Canonical
Knowledge Unit != RAG Chunk
Canonical Wiki != RAG Index
AI Draft != Approved Knowledge
External Consumer != xmg-kb Runtime
Deployment != Verified
Code Exists != PASS
```

## 5. 当前组件基线

```text
BookStack
+
Prefect
+
Docling Serve
+
MinerU fallback
+
LibreOffice / ClamAV
+
RAGFlow
+
Langfuse
+
Simple Curator
+
KAG POC (optional)
```

自定义代码只做 Adapter、Schema、Policy、Prompt、Flow、Mapping、Sync、API、MCP Safety Layer 和 Tests。

## 6. 历史资产处理原则

提前存在的 Manifest、Mapping、Parsed、Provenance 等资产属于 `PRE_EXISTING_REUSABLE_ASSET`。

它们需要按当前 Gate 重新验收，但不因阶段顺序偏差自动删除、重跑或重新调用昂贵模型。

原则：

```text
Legacy First
Raw Fallback
```

## 7. 核心组件替换规则

任何替换核心组件的提议都必须有 ADR，并至少说明：当前组件的实测缺口、新组件成熟度、License、API 稳定性、迁移成本、Data Portability、Benchmark 和 Rollback。

没有证据，不因为“更流行”或“更新”替换主链。