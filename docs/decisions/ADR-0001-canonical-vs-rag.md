# ADR-0001：Canonical 文件与 RAG 派生索引分离

- Status: Accepted
- Context: 企业知识必须能脱离特定 Wiki、数据库或检索引擎独立保存、读取、编辑和恢复。
- Decision: 本地文件系统中的 Canonical Knowledge 是唯一知识事实源；RAG Index 是可重建的派生数据。索引必须保留文件 ID/路径、内容 hash、来源和版本映射。Wiki UI 与 GitLab 同步不属于当前生产管线。
- Consequences: 不得把 RAGFlow、Wiki 数据库或 GitLab 作为唯一原文存储。Canonical 文件必须可独立备份恢复；索引可从文件重新构建。
- Alternatives: 以 Wiki 数据库或向量库作为唯一知识源；均不采用。
- Validation: 通过代表性文件验证可追溯、索引重建、增量更新和旧索引回退。
- Rollback: 如需改变 Canonical Store，必须新建 ADR，并完成导出、hash、资产/链接检查和恢复演练。
