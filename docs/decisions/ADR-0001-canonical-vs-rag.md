# ADR-0001：Canonical Wiki 与 RAG Index 分离

**Status:** Accepted

## Context

原始资料、人工正式知识和 RAG Chunk 具有不同生命周期。如果混在同一个检索库中，会重新引入重复、历史版本、冲突和不可追溯内容。

## Decision

采用：

```text
Evidence
→ Governance
→ BookStack Canonical
→ RAGFlow Derived Index
```

Production RAG 只接受 Canonical Wiki。

## Consequences

优点：

- 人类事实源唯一；
- RAG 可随时重建；
- AI QA 不直接接触 Raw；
- Version/Conflict 先治理再检索。

成本：

- 需要 Wiki → RAG 增量同步；
- 需要稳定 Page/Revision Mapping。

## Validation

通过 Gold QA 和 Revision Update Test 验证。

## Rollback

RAGFlow 可回滚至上一有效 Wiki Revision；Canonical 不依赖 RAGFlow 存活。
