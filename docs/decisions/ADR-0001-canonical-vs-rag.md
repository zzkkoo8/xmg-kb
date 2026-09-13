# ADR-0001：Canonical Wiki 与 RAG Index 分离

**Status:** Accepted

## Context

原始资料、人工正式知识和 RAG Chunk 具有不同生命周期。如果混在同一个检索库中，会重新引入重复、历史版本、冲突和不可追溯内容。

## Decision

采用：

```text
Evidence
→ Governance
→ Canonical Wiki
→ RAGFlow Derived Index
```

Production RAG 只接受 Canonical Wiki。

当前默认 Wiki 实现由后续 ADR 决定；本 ADR 只固定“Canonical 与 RAG 分离”的长期架构约束。

## Consequences

优点：

- 人类事实源唯一；
- RAG 可随时重建；
- AI QA/外部消费者不直接依赖 Raw；
- Version/Conflict 先治理再检索；
- Wiki 实现可通过 Adapter 替换，不影响 RAG 角色定义。

成本：

- 需要 Wiki → RAG 增量同步；
- 需要稳定 Canonical/Page/Revision Mapping。

## Validation

通过 Gold QA、Revision Update Test、Source Traceability 和 Restore Test 验证。

## Rollback

RAGFlow 可回滚到上一有效 Wiki Revision；Canonical 不依赖 RAGFlow 存活。