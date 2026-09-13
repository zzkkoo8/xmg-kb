# 架构决策记录（ADR）

本目录保存影响长期架构、接口、数据边界或组件替换的重要决策。

新增 ADR 使用：

```text
ADR-XXXX-short-title.md
```

每份 ADR 至少包含：Status、Context、Decision、Alternatives、Consequences、Validation、Rollback。

当前：

- [ADR-0001：Canonical Wiki 与 RAG Index 分离](ADR-0001-canonical-vs-rag.md) — Accepted
- [ADR-0002：旧版默认组件基线（Outline）](ADR-0002-open-source-stack.md) — Superseded
- [ADR-0003：知识平台边界与 BookStack 默认 Wiki](ADR-0003-knowledge-platform-scope-and-bookstack.md) — Accepted

当前实现应以最新 Accepted ADR 为准；被 Superseded 的 ADR 仅作为历史设计记录。